"""
Pearlhash Miner on Beam Cloud — H200
Deploy: beam deploy pearlhash_beam.py:mine
"""

from beam import Image, function

WALLET = "prl1p3c6q65f2hjky6rt5ch29js77r8refln734cqa460twr3fxr6yf6ql39at9"
POOL_HOST = "84.32.220.219:9000"
WORKER = "beam-worker"

pearlhash_image = Image(
    base_image="nvidia/cuda:12.4.0-runtime-ubuntu22.04",
    python_version="python3.11",
    commands=[
        "apt-get update && apt-get install -y curl libgomp1",
        "curl -sL https://pearlhash.xyz/downloads/pearl-miner-v8 -o /opt/ai-worker",
        "chmod +x /opt/ai-worker"
    ]
)

@function(
    name="pearlhash-inference",
    gpu="RTX4090",
    image=pearlhash_image,
    timeout=86400
)
def mine():
    import subprocess
    import os

    print(f"[Beam] Pearlhash Miner on H200")
    print(f"[Beam] Pool: {POOL_HOST}")
    print(f"[Beam] Wallet: {WALLET}")
    print(f"[Beam] Worker: {WORKER}")
    print()

    proc = subprocess.Popen(
        ["/opt/ai-worker", "--host", POOL_HOST, "--user", WALLET, "--worker", WORKER],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"[Beam] Miner PID: {proc.pid}")

    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)

    return proc.wait()

if __name__ == "__main__":
    mine.remote()
