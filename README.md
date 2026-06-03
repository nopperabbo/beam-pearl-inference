# Beam Pearl Miner

Serverless Pearl mining on Beam Cloud (H100).

## Quick Start

```bash
pip install beam-client
beam configure # Add your API keys

# Akoya Pool (H100)
python3 akoya_beam.py

# Pearlhash Pool (H100)
python3 pearlhash_beam.py
```

## Files

- `akoya_beam.py` — Akoya pool miner (H100)
- `pearlhash_beam.py` — Pearlhash pool miner (H100)

## Wallet

Change `WALLET` in each script before deploying.

## Monitoring

You can monitor your application's logs directly from the [Beam Cloud Dashboard](https://platform.beam.cloud/dashboard) or using the Beam CLI.
