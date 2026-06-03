# Beam Pearl Miner

Serverless Pearl mining on Beam Cloud (RTX4090).

## Quick Start

```bash
# Clone the repository
git clone https://github.com/nopperabbo/beam-pearl-inference.git
cd beam-pearl-inference

# Install Beam CLI and configure
pip install beam-client
beam configure # Add your API keys

# Akoya Pool (RTX4090)
python3 akoya_beam.py

# Pearlhash Pool (RTX4090)
python3 pearlhash_beam.py
```

## Files

- `akoya_beam.py` — Akoya pool miner (RTX4090)
- `pearlhash_beam.py` — Pearlhash pool miner (RTX4090)

## Wallet

Change `WALLET` in each script before deploying.

## Monitoring

You can monitor your application's logs directly from the [Beam Cloud Dashboard](https://platform.beam.cloud/dashboard) or using the Beam CLI.
