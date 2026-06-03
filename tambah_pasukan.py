import subprocess
import os
import sys

# Number of ADDITIONAL workers to launch
NUM_ADDITIONAL = 2
START_INDEX = 2 # Start naming from beam-worker-2

print(f"🚀 NAMBAH PASUKAN: Launching {NUM_ADDITIONAL} additional miners on Beam Cloud...")

processes = []

for i in range(NUM_ADDITIONAL):
    worker_index = START_INDEX + i
    worker_name = f"beam-worker-{worker_index}"
    print(f"Starting {worker_name}...")
    
    env = os.environ.copy()
    env["WORKER_NAME"] = worker_name
    
    p = subprocess.Popen(
        [sys.executable, "akoya_beam.py"],
        env=env
    )
    processes.append(p)

print("\n🔥 2 Pasukan tambahan udah dikirim buat nemenin worker 1!")
print("Logs pasukan baru bakal numpuk di bawah sini.")
print("Press Ctrl+C to stop THESE TWO workers.")
print("-" * 50)

try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n[Gasak] Ctrl+C detected! Terminating pasukan tambahan...")
    for p in processes:
        p.terminate()
    print("[Gasak] Pasukan tambahan stopped.")
