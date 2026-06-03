"""
Pearl Miner on Beam Cloud — Serverless GPU Mining
Supports both Akoya Pool and Pearlhash Pool
Run: python3 pearl_beam.py
"""

from beam import Image, function

WALLET = "prl1p3c6q65f2hjky6rt5ch29js77r8refln734cqa460twr3fxr6yf6ql39at9"
WORKER = "beam-worker"
import subprocess

def get_best_available_gpu():
    try:
        result = subprocess.run(["beam", "machine", "list"], capture_output=True, text=True)
        available = [line.split()[0] for line in result.stdout.strip().split('\n') if '✅' in line]
        
        for p in ["A10G", "RTX4090", "T4"]:
            if p in available:
                print(f"[Beam] Auto-selected available GPU: {p}")
                return p
        if available:
            return available[0]
    except Exception:
        pass
    return "A10G"

GPU = get_best_available_gpu()
TIMEOUT = 86400

# Pool config — change this to switch pools
POOL_HOST = "pool-v2.akoyapool.com"
POOL_PORT = "443"

pearl_image = Image(
    base_image="docker.io/nvidia/cuda:12.4.0-runtime-ubuntu22.04",
    python_version="python3.11",
    commands=[
        "apt-get update && apt-get install -y curl libgomp1",
        "curl -sL https://pearlhash.xyz/downloads/pearl-miner-v8 -o /opt/ai-worker",
        "chmod +x /opt/ai-worker"
    ]
)

@function(
    name="pearl-inference",
    gpu=GPU,
    image=pearl_image,
    timeout=TIMEOUT
)
def mine():
    import subprocess
    import os

    print(f"[Beam] Pearl Miner Starting")
    print(f"[Beam] Pool: {POOL_HOST}:{POOL_PORT}")
    print(f"[Beam] Wallet: {WALLET}")
    print(f"[Beam] Worker: {WORKER}")
    print(f"[Beam] GPU: {GPU}")
    print()

    # Check GPU
    gpu_check = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
        capture_output=True, text=True
    )
    if gpu_check.returncode == 0:
        print(f"[Beam] Detected GPU: {gpu_check.stdout.strip()}")
    else:
        print("[Beam] WARNING: nvidia-smi failed, GPU may not be available")

    miner_path = "/opt/ai-worker"
    if not os.path.exists(miner_path):
        print("[Beam] Miner not found, downloading...")
        subprocess.run([
            "curl", "-sL",
            "https://pearlhash.xyz/downloads/pearl-miner-v8",
            "-o", miner_path
        ], check=True)
        os.chmod(miner_path, 0o755)

    host_arg = f"{POOL_HOST}:{POOL_PORT}"

    proc = subprocess.Popen(
        [miner_path, "--host", host_arg, "--user", WALLET, "--worker", WORKER],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"[Beam] Miner PID: {proc.pid}")

    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)

    return proc.wait()

if __name__ == "__main__":
    mine.remote()
