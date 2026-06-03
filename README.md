# Beam Pearl Miner

Serverless Pearl mining on Beam Cloud (H100/H200).

## Quick Start

```bash
pip install beam-client
beam configure # Add your API keys

# Akoya Pool (H200)
beam run akoya_beam.py:mine

# Pearlhash Pool (H200)
beam run pearlhash_beam.py:mine
```

## Files

- `akoya_beam.py` — Akoya pool miner (H200)
- `pearlhash_beam.py` — Pearlhash pool miner (H200)

## Wallet

Change `WALLET` in each script before deploying.

## Monitoring

You can monitor your application's logs directly from the [Beam Cloud Dashboard](https://platform.beam.cloud/dashboard) or using the Beam CLI.
