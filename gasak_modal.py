"""
GASAK MODE for Modal.com
Launches multiple workers with staggered timing to avoid quota limits
Same strategy as Beam Cloud gasak_semua.py
"""
import subprocess
import os
import sys
import time

# Config
NUM_WORKERS = 3
DELAY_BETWEEN = 45  # seconds between launches (learned from Beam)
GPU_TYPE = "H100"    # H100 > A100-80GB > A100-40GB > A10G > L40S

print(f"🚀 MODAL GASAK MODE")
print(f"   Workers: {NUM_WORKERS}")
print(f"   GPU: {GPU_TYPE}")
print(f"   Delay: {DELAY_BETWEEN}s between launches")
print(f"{'='*50}")

processes = []

for i in range(NUM_WORKERS):
    worker_name = f"modal-worker-{i+1}"
    
    if i > 0:
        print(f"\n⏳ Cooling down {DELAY_BETWEEN}s...")
        time.sleep(DELAY_BETWEEN)
    
    print(f"\n🎰 Launching {worker_name} on {GPU_TYPE}...")
    
    env = os.environ.copy()
    env["WORKER_NAME"] = worker_name
    env["GPU_TYPE"] = GPU_TYPE
    
    p = subprocess.Popen(
        [sys.executable, "-m", "modal", "run", "modal_pearl.py"],
        env=env
    )
    processes.append((worker_name, p))
    print(f"✅ {worker_name} dispatched! (PID: {p.pid})")

print(f"\n{'='*50}")
print(f"🔥 All {NUM_WORKERS} Modal workers launched on {GPU_TYPE}!")
print(f"📊 Check hashrate: https://akoyapool.com")
print(f"💰 Wallet: prl1pftz2ev8450xq9vau4a8ls48tnqmra8a28lkyhrqyu593msfvyhlqej784c")
print(f"Press Ctrl+C to stop all workers.")
print(f"{'='*50}\n")

try:
    for name, p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n[Stop] Terminating all Modal workers...")
    for name, p in processes:
        p.terminate()
        print(f"  Stopped {name}")
    print("[Stop] All stopped.")
