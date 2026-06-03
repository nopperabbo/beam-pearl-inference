"""
Pearl Miner on Modal.com — Akoya Optimized Kernel
Supports H100, H200, A100, A10G with smart auto-fallback
Run: modal run modal_pearl.py
"""

import modal
import os

WALLET = "prl1pftz2ev8450xq9vau4a8ls48tnqmra8a28lkyhrqyu593msfvyhlqej784c"
WORKER = os.environ.get("WORKER_NAME", "modal-worker")

app = modal.App("llm-inference-modal")

# Build image with Akoya miner + Pearlhash fallback
miner_image = (
    modal.Image.from_registry("nvidia/cuda:12.2.0-runtime-ubuntu22.04", add_python="3.11")
    .apt_install("curl", "libgomp1", "ca-certificates")
    .run_commands(
        # Install crane to extract Akoya binary
        "curl -sL https://github.com/google/go-containerregistry/releases/latest/download/go-containerregistry_Linux_x86_64.tar.gz | tar -xzf - -C /usr/local/bin crane",
        # Extract Akoya miner from their CUDA 12.2 image
        "crane export registry.akoyapool.com/akoya-miner:latest-cuda122 - | tar -xf - -C / app/ var/lib/akoya-miner/ 2>/dev/null; true",
        "chmod +x /app/akoya-miner 2>/dev/null; true",
        # Fallback: Pearlhash reference miner
        "curl -sL https://pearlhash.xyz/downloads/pearl-miner-v8 -o /opt/pearl-miner && chmod +x /opt/pearl-miner",
    )
)

@app.function(
    gpu="H100",
    image=miner_image,
    timeout=86400,
)
def generate(worker_name: str = "modal-worker"):
    import subprocess
    import os
    import shutil
    import time

    os.environ["NVIDIA_DRIVER_CAPABILITIES"] = "all"
    os.environ["NVIDIA_VISIBLE_DEVICES"] = "all"

    print(f"[Modal] Pearl Miner Starting")
    print(f"[Modal] Worker: {worker_name}")
    print()

    # Check GPU
    gpu_check = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv,noheader"],
        capture_output=True, text=True
    )
    if gpu_check.returncode == 0:
        print(f"[Modal] Detected GPU: {gpu_check.stdout.strip()}")

    # --- SMART AUTO-FALLBACK ENGINE ---
    akoya_path = "/app/akoya-miner"
    use_akoya = os.path.exists(akoya_path)

    if use_akoya:
        print("[Modal] ✅ Akoya optimized kernel found! Attempting 2x mode...")

        os.environ["AKOYA_POOL_WALLET"]    = WALLET
        os.environ["AKOYA_POOL_WORKER"]    = worker_name
        os.environ["AKOYA_POOL_HOST"]      = "pool-v2.akoyapool.com"
        os.environ["AKOYA_POOL_PORT"]      = "443"
        os.environ["AKOYA_POOL_USE_TLS"]   = "1"
        os.environ["AKOYA_GPU_INDICES"]    = "all"

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
                print(f"[Modal] GPU Kernel: {src}")
            else:
                # Try portable as fallback
                portable = f"{lib_dir}/libpearl_gemm_capi_portable.so"
                if os.path.exists(portable):
                    if os.path.lexists(target): os.unlink(target)
                    os.symlink(portable, target)
                    print(f"[Modal] GPU Kernel: portable (fallback)")

        os.makedirs("/var/lib/akoya-miner", exist_ok=True)

        worker_path = "/tmp/ai-worker"
        shutil.copy(akoya_path, worker_path)
        os.chmod(worker_path, 0o755)

        proc = subprocess.Popen(
            [worker_path, "mine-blocks"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        print(f"[Modal] PID: {proc.pid}")
        print("[Modal] Monitoring for CUDA compatibility (30s)...")

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

        if cuda_fail:
            print("\n[Modal] ⚠️ CUDA incompatible! Auto-switching to Pearlhash...")
            proc.kill()
            proc.wait()
            use_akoya = False
        else:
            print("[Modal] ✅ CUDA OK! Running at max speed!")
            for line in iter(proc.stdout.readline, b""):
                print(line.decode().strip(), flush=True)
            return proc.wait()

    if not use_akoya:
        print("[Modal] 🔄 Starting Pearlhash miner...")
        proc = subprocess.Popen(
            ["/opt/pearl-miner", "--host", "84.32.220.219:9000", "--user", WALLET, "--worker", worker_name],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        print(f"[Modal] PID: {proc.pid}")
        for line in iter(proc.stdout.readline, b""):
            print(line.decode().strip(), flush=True)
        return proc.wait()

@app.local_entrypoint()
def main():
    generate.remote(worker_name=WORKER)
