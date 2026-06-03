import subprocess
import os
import sys

# Number of GPUs to gasak
NUM_WORKERS = 3

print(f"🚀 GASAK MODE: Launching {NUM_WORKERS} concurrent miners on Beam Cloud...")

processes = []

for i in range(NUM_WORKERS):
    worker_name = f"beam-worker-{i+1}"
    print(f"Starting {worker_name}...")
    
    # Copy current env vars and add specific worker name
    env = os.environ.copy()
    env["WORKER_NAME"] = worker_name
    
    # Start the process without blocking
    p = subprocess.Popen(
        [sys.executable, "pearl_beam.py"],
        env=env
    )
    processes.append(p)

print("\n🔥 All 3 miners have been dispatched to Beam Cloud!")
print("Their logs will interleave below (don't panic if it looks messy).")
print("Press Ctrl+C to stop all of them.")
print("-" * 50)

# Wait for all of them (keeps the main script alive)
try:
    for p in processes:
        p.wait()
except KeyboardInterrupt:
    print("\n[Gasak] Ctrl+C detected! Terminating all workers...")
    for p in processes:
        p.terminate()
    print("[Gasak] Stopped.")
