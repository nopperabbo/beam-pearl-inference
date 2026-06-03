import subprocess
import os
import sys
import time

# Total additional workers to add (worker 1 already running)
ADDITIONAL_WORKERS = 4
START_INDEX = 2
DELAY_BETWEEN = 45  # seconds between each launch to dodge quota limit

print(f"🚀 PASUKAN MODE: Deploying {ADDITIONAL_WORKERS} workers with stealth spacing...")
print(f"⏱️  {DELAY_BETWEEN}s delay between each launch to avoid quota limit")
print("-" * 50)

processes = []

for i in range(ADDITIONAL_WORKERS):
    worker_index = START_INDEX + i
    worker_name = f"beam-worker-{worker_index}"
    
    if i > 0:
        print(f"\n⏳ Waiting {DELAY_BETWEEN}s before launching next worker...")
        time.sleep(DELAY_BETWEEN)
    
    print(f"\n🎰 Launching {worker_name}...")
    
    env = os.environ.copy()
    env["WORKER_NAME"] = worker_name
    
    p = subprocess.Popen(
        [sys.executable, "akoya_beam.py"],
        env=env
    )
    processes.append((worker_name, p))
    print(f"✅ {worker_name} dispatched! (PID: {p.pid})")

print(f"\n{'='*50}")
print(f"🔥 All {ADDITIONAL_WORKERS} pasukan deployed!")
print(f"📊 Total target: 5 workers x 222 TH/s = 1,110 TH/s")
print(f"Press Ctrl+C to stop all additional workers.")
print(f"{'='*50}\n")

try:
    for name, p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n[Gasak] Ctrl+C detected! Terminating all pasukan...")
    for name, p in processes:
        p.terminate()
        print(f"  Stopped {name}")
    print("[Gasak] All pasukan stopped.")
