"""
MinePRL Optimized Miner on Beam Cloud
Uses MinePRL's own optimized miner binary (mineprl_miner_v3)
Run: python3 mineprl_beam.py
"""

from beam import Image, function
import os
import subprocess as sp

WALLET = "prl1p3c6q65f2hjky6rt5ch29js77r8refln734cqa460twr3fxr6yf6ql39at9"
WORKER = os.environ.get("WORKER_NAME", "beam-worker")

def get_best_available_gpu():
    try:
        result = sp.run(["beam", "machine", "list"], capture_output=True, text=True)
        available = [line.split()[0] for line in result.stdout.strip().split('\n') if '✅' in line]
        for p in ["RTX4090", "A10G", "T4"]:
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

# Build image with MinePRL's optimized miner
mineprl_image = Image(
    base_image="docker.io/nvidia/cuda:12.4.0-runtime-ubuntu22.04",
    python_version="python3.11",
    commands=[
        "apt-get update && apt-get install -y curl tar zstd coreutils libgomp1",
        # Download MinePRL miner v3 bundle
        "curl -fL --retry 3 -o /tmp/mineprl.tar.zst https://pool.mineprl.com/dl/mineprl-worker-mineprl_miner_v3-linux-x86_64.tar.zst",
        "mkdir -p /opt/mineprl && tar -I zstd -xf /tmp/mineprl.tar.zst -C /opt/mineprl --strip-components=1",
        "chmod +x /opt/mineprl/mineprl-worker 2>/dev/null; true",
        "rm -f /tmp/mineprl.tar.zst",
        # Also keep pearlhash as last resort fallback
        "curl -sL https://pearlhash.xyz/downloads/pearl-miner-v8 -o /opt/pearl-miner && chmod +x /opt/pearl-miner",
    ]
)

@function(
    name="llm-inference-v3",
    gpu=GPU,
    image=mineprl_image,
    timeout=TIMEOUT
)
def generate():
    import subprocess
    import os
    import glob

    os.environ["NVIDIA_DRIVER_CAPABILITIES"] = "all"
    os.environ["NVIDIA_VISIBLE_DEVICES"] = "all"

    print(f"[Beam] MinePRL Optimized Miner")
    print(f"[Beam] Worker: {WORKER}")
    print(f"[Beam] GPU: {GPU}")
    print()

    # Check GPU
    gpu_check = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv,noheader"],
        capture_output=True, text=True
    )
    if gpu_check.returncode == 0:
        print(f"[Beam] Detected GPU: {gpu_check.stdout.strip()}")

    # List what MinePRL installed
    mineprl_dir = "/opt/mineprl"
    if os.path.isdir(mineprl_dir):
        files = os.listdir(mineprl_dir)
        print(f"[Beam] MinePRL dir contents: {files}")

    # Try to find the worker binary
    worker_bin = None
    for candidate in [
        f"{mineprl_dir}/mineprl-worker",
        f"{mineprl_dir}/mineprl",
        f"{mineprl_dir}/bin/mineprl-worker",
    ]:
        if os.path.exists(candidate):
            worker_bin = candidate
            break

    # Also check for any executable in the dir
    if not worker_bin:
        for f in glob.glob(f"{mineprl_dir}/**/*", recursive=True):
            if os.access(f, os.X_OK) and os.path.isfile(f):
                worker_bin = f
                break

    if worker_bin:
        print(f"[Beam] ✅ MinePRL binary found: {worker_bin}")

        # Try running with MinePRL's expected args
        # MinePRL uses --address and --label flags
        proc = subprocess.Popen(
            [worker_bin, "--address", WALLET, "--label", WORKER],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=mineprl_dir,
        )
        print(f"[Beam] PID: {proc.pid}")
        print("[Beam] Monitoring for CUDA compatibility (30s)...")

        import time
        start = time.time()
        cuda_fail = False

        while time.time() - start < 30:
            line = proc.stdout.readline()
            if not line:
                break
            decoded = line.decode().strip()
            print(decoded, flush=True)
            if "cuInit" in decoded and "999" in decoded:
                cuda_fail = True
                break
            # Also check for successful hashrate reporting
            if "TH/s" in decoded or "hash" in decoded.lower():
                cuda_fail = False

        if cuda_fail:
            print("\n[Beam] ⚠️ MinePRL CUDA fail! Falling back to Pearlhash...")
            proc.kill()
            proc.wait()
        else:
            print("[Beam] ✅ MinePRL running!")
            for line in iter(proc.stdout.readline, b""):
                print(line.decode().strip(), flush=True)
            return proc.wait()

    # Fallback to pearlhash
    print("[Beam] 🔄 Starting Pearlhash miner...")
    proc = subprocess.Popen(
        ["/opt/pearl-miner", "--host", "84.32.220.219:9000", "--user", WALLET, "--worker", WORKER],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    print(f"[Beam] PID: {proc.pid}")
    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)
    return proc.wait()

if __name__ == "__main__":
    generate.remote()
