import subprocess
import os
import sys
import time

# Add 2 more workers to fill remaining GPU slots (3/5 currently used)
NUM_ADDITIONAL = 2
START_INDEX = 4  # beam-worker-4 and beam-worker-5
DELAY_BETWEEN = 60  # 60s delay to be safe with quota

print(f"🚀 FINAL PUSH: Adding {NUM_ADDITIONAL} more RTX 4090s to reach 5/5 GPU quota!")
print(f"⏱️  {DELAY_BETWEEN}s delay between launches")
print("-" * 50)

processes = []

for i in range(NUM_ADDITIONAL):
    worker_index = START_INDEX + i
    worker_name = f"beam-worker-{worker_index}"
    
    if i > 0:
        print(f"\n⏳ Cooling down {DELAY_BETWEEN}s before next launch...")
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
print(f"🔥 Target: 5/5 GPUs = ~900 TH/s!")
print(f"Press Ctrl+C to stop these workers only.")
print(f"{'='*50}\n")

try:
    for name, p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n[Stop] Terminating additional workers...")
    for name, p in processes:
        p.terminate()
        print(f"  Stopped {name}")
