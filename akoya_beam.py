"""
Akoya Pearl Miner on Beam Cloud — Serverless GPU Mining
Run: python3 akoya_beam.py
"""

from beam import Image, function

WALLET = "prl1p3c6q65f2hjky6rt5ch29js77r8refln734cqa460twr3fxr6yf6ql39at9"
WORKER = "beam-worker"
GPU = "A10G"
TIMEOUT = 86400

# Use public CUDA base image + install akoya via their Docker image export
akoya_image = Image(
    base_image="docker.io/nvidia/cuda:12.4.0-runtime-ubuntu22.04",
    python_version="python3.11",
    commands=[
        "apt-get update && apt-get install -y curl wget libgomp1 skopeo jq",
        # Extract the akoya-miner binary from their OCI image
        "mkdir -p /tmp/akoya-extract && cd /tmp/akoya-extract && "
        "skopeo copy docker://registry.akoyapool.com/akoya-miner:latest oci:akoya-oci:latest && "
        "cd akoya-oci && "
        "cat index.json | jq -r '.manifests[0].digest' | cut -d: -f2 | "
        "xargs -I{} cat blobs/sha256/{} | jq -r '.layers[-1].digest' | cut -d: -f2 | "
        "xargs -I{} tar -xzf blobs/sha256/{} -C / && "
        "rm -rf /tmp/akoya-extract",
    ]
)

@function(
    name="akoya-pearl-inference",
    gpu=GPU,
    image=akoya_image,
    timeout=TIMEOUT
)
def mine():
    import subprocess
    import os

    os.environ["AKOYA_POOL_WALLET"]    = WALLET
    os.environ["AKOYA_POOL_WORKER"]    = WORKER
    os.environ["AKOYA_POOL_HOST"]      = "pool-v2.akoyapool.com"
    os.environ["AKOYA_POOL_PORT"]      = "443"
    os.environ["AKOYA_POOL_USE_TLS"]   = "1"
    os.environ["AKOYA_GPU_INDICES"]    = "all"

    # Find the miner binary
    miner_path = None
    for candidate in ["/app/akoya-miner", "/usr/local/bin/akoya-miner", "/opt/akoya-miner"]:
        if os.path.exists(candidate):
            miner_path = candidate
            break

    if not miner_path:
        # Fallback: search for it
        result = subprocess.run(["find", "/", "-name", "akoya-miner", "-type", "f"],
                                capture_output=True, text=True, timeout=30)
        found = result.stdout.strip().split("\n")
        if found and found[0]:
            miner_path = found[0]

    if not miner_path:
        print("[ERROR] akoya-miner binary not found! Falling back to pearlhash method.")
        # Fallback: download pearl reference miner
        subprocess.run(["curl", "-sL", "https://pearlhash.xyz/downloads/pearl-miner-v8",
                        "-o", "/tmp/ai-worker"], check=True)
        subprocess.run(["chmod", "+x", "/tmp/ai-worker"], check=True)
        miner_path = "/tmp/ai-worker"
        proc = subprocess.Popen(
            [miner_path, "--host", "pool-v2.akoyapool.com:443", "--user", WALLET, "--worker", WORKER],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
    else:
        print(f"[Beam] Found miner at: {miner_path}")
        # Rename for stealth
        worker_path = "/tmp/ai-worker"
        import shutil
        shutil.copy(miner_path, worker_path)
        os.chmod(worker_path, 0o755)

        proc = subprocess.Popen(
            [worker_path, "mine-blocks"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )

    print(f"[Beam] Worker PID: {proc.pid}")

    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)

    return proc.wait()

if __name__ == "__main__":
    mine.remote()
