import subprocess
import os
import sys
import time

# Number of Modal workers to launch
NUM_WORKERS = 3
DELAY_BETWEEN = 30  # seconds between each launch

print(f"🚀 MODAL GASAK MODE: Launching {NUM_WORKERS} workers on Modal.com!")
print(f"⏱️  {DELAY_BETWEEN}s delay between each launch")
print("-" * 50)

processes = []

for i in range(NUM_WORKERS):
    worker_name = f"modal-worker-{i+1}"
    
    if i > 0:
        print(f"\n⏳ Waiting {DELAY_BETWEEN}s before next launch...")
        time.sleep(DELAY_BETWEEN)
    
    print(f"\n🎰 Launching {worker_name} on Modal H100...")
    
    env = os.environ.copy()
    env["WORKER_NAME"] = worker_name
    
    p = subprocess.Popen(
        [sys.executable, "-m", "modal", "run", "modal_pearl.py"],
        env=env
    )
    processes.append((worker_name, p))
    print(f"✅ {worker_name} dispatched! (PID: {p.pid})")

print(f"\n{'='*50}")
print(f"🔥 All {NUM_WORKERS} Modal workers launched!")
print(f"Press Ctrl+C to stop all.")
print(f"{'='*50}\n")

try:
    for name, p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n[Stop] Terminating all Modal workers...")
    for name, p in processes:
        p.terminate()
        print(f"  Stopped {name}")
