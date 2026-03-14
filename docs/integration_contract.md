# Integration Contract

This document defines the production contract exposed by `crypto-leader-rotation` to downstream strategy systems.

The upstream project publishes a monthly `core_major` live pool and exposes it through:

1. local build artifacts under `data/output/`
2. versioned and current objects in GCS
3. a lightweight Firestore summary document

## Canonical Downstream Files

### `live_pool_legacy.json`

This is the most convenient file for older downstream scripts that expect a direct symbol mapping.

Schema:

```json
{
  "as_of_date": "2026-03-13",
  "version": "2026-03-13-core_major",
  "mode": "core_major",
  "pool_size": 5,
  "symbols": {
    "TRXUSDT": {"base_asset": "TRX"},
    "ETHUSDT": {"base_asset": "ETH"},
    "BCHUSDT": {"base_asset": "BCH"},
    "NEARUSDT": {"base_asset": "NEAR"},
    "LTCUSDT": {"base_asset": "LTC"}
  },
  "symbol_map": {
    "TRXUSDT": {"base_asset": "TRX"},
    "ETHUSDT": {"base_asset": "ETH"},
    "BCHUSDT": {"base_asset": "BCH"},
    "NEARUSDT": {"base_asset": "NEAR"},
    "LTCUSDT": {"base_asset": "LTC"}
  },
  "source_project": "crypto-leader-rotation"
}
```

Contract notes:

- `as_of_date`: the production snapshot date in `YYYY-MM-DD`
- `version`: stable release identifier, typically `<YYYY-MM-DD>-<mode>`
- `mode`: the published production mode, currently `core_major`
- `pool_size`: number of symbols currently published
- `symbols`: mapping from `SYMBOLUSDT` to `{base_asset}`
- `symbol_map`: additive alias of the same mapping for downstreams that use the richer contract
- `source_project`: upstream publisher identity for observability and audit trails
- keys are the production `core_major` pool unless explicitly overridden during build

### `live_pool.json`

This file contains both the ordered list and the symbol mapping:

```json
{
  "as_of_date": "2026-03-13",
  "version": "2026-03-13-core_major",
  "mode": "core_major",
  "pool_size": 5,
  "symbols": ["TRXUSDT", "ETHUSDT", "BCHUSDT", "NEARUSDT", "LTCUSDT"],
  "symbol_map": {
    "TRXUSDT": {"base_asset": "TRX"},
    "ETHUSDT": {"base_asset": "ETH"},
    "BCHUSDT": {"base_asset": "BCH"},
    "NEARUSDT": {"base_asset": "NEAR"},
    "LTCUSDT": {"base_asset": "LTC"}
  },
  "source_project": "crypto-leader-rotation"
}
```

Stable contract fields for downstream validation:

- `as_of_date`
- `version`
- `mode`
- `pool_size`
- `symbols`
- `symbol_map`
- `source_project`

Research/reporting extras are intentionally not part of the stable contract. Downstream consumers should not infer live readiness from local research CSVs or validation summaries.

Optional additive research extension:

- `selection_meta` may be included in local shadow-release artifacts, or in live exports if explicitly enabled
- example fields include `final_score`, `confidence`, and `current_rank`
- downstream should treat this as optional enrichment, not as a required contract field

## Firestore Contract

Collection and document defaults:

- collection: `strategy`
- document: `CRYPTO_LEADER_ROTATION_LIVE_POOL`

Payload example:

```json
{
  "as_of_date": "2026-03-13",
  "mode": "core_major",
  "version": "2026-03-13-core_major",
  "pool_size": 5,
  "symbols": ["TRXUSDT", "ETHUSDT", "BCHUSDT", "NEARUSDT", "LTCUSDT"],
  "symbol_map": {
    "TRXUSDT": {"base_asset": "TRX"},
    "ETHUSDT": {"base_asset": "ETH"},
    "BCHUSDT": {"base_asset": "BCH"},
    "NEARUSDT": {"base_asset": "NEAR"},
    "LTCUSDT": {"base_asset": "LTC"}
  },
  "storage_prefix": "gs://example-bucket/crypto-leader-rotation/releases/2026-03-13-core_major",
  "current_prefix": "gs://example-bucket/crypto-leader-rotation/current",
  "live_pool_legacy_uri": "gs://example-bucket/crypto-leader-rotation/current/live_pool_legacy.json",
  "live_pool_uri": "gs://example-bucket/crypto-leader-rotation/current/live_pool.json",
  "latest_universe_uri": "gs://example-bucket/crypto-leader-rotation/current/latest_universe.json",
  "latest_ranking_uri": "gs://example-bucket/crypto-leader-rotation/current/latest_ranking.csv",
  "versioned_live_pool_legacy_uri": "gs://example-bucket/crypto-leader-rotation/releases/2026-03-13-core_major/live_pool_legacy.json",
  "generated_at": "2026-03-13T13:00:00+00:00",
  "source_project": "crypto-leader-rotation"
}
```

The Firestore document intentionally excludes the full ranking CSV. Downstream readers should only rely on the summary fields above.

Stable vs additive fields:

- stable core fields: `as_of_date`, `version`, `mode`, `pool_size`, `symbols`, `symbol_map`, `source_project`
- publish-only pointer fields: `storage_prefix`, `current_prefix`, `live_pool_uri`, `live_pool_legacy_uri`, `latest_universe_uri`, `latest_ranking_uri`, `versioned_live_pool_legacy_uri`
- additive observability field: `generated_at`

## GCS Path Layout

Versioned release objects:

```text
gs://<bucket>/crypto-leader-rotation/releases/<YYYY-MM-DD-mode>/latest_universe.json
gs://<bucket>/crypto-leader-rotation/releases/<YYYY-MM-DD-mode>/latest_ranking.csv
gs://<bucket>/crypto-leader-rotation/releases/<YYYY-MM-DD-mode>/live_pool.json
gs://<bucket>/crypto-leader-rotation/releases/<YYYY-MM-DD-mode>/live_pool_legacy.json
```

Current pointers:

```text
gs://<bucket>/crypto-leader-rotation/current/latest_universe.json
gs://<bucket>/crypto-leader-rotation/current/latest_ranking.csv
gs://<bucket>/crypto-leader-rotation/current/live_pool.json
gs://<bucket>/crypto-leader-rotation/current/live_pool_legacy.json
```

## Local Shadow Release History

For end-to-end offline replay, the repository can also build a local monthly shadow release history under:

```text
data/output/shadow_releases/
  release_index.csv
  <YYYY-MM-DD-mode>/
    live_pool.json
    live_pool_legacy.json
    release_manifest.json
```

`release_index.csv` is intended for downstream local replay and includes:

- `as_of_date`
- `activation_date`
- `version`
- `mode`
- `pool_size`
- `symbols`
- optional research diagnostics such as `regime` and `regime_confidence`
- relative paths to the local artifact files

This shadow history is additive research infrastructure. It is meant to mimic the monthly upstream artifact sequence without requiring live Firestore or GCS.

## Shadow Candidate Tracks

For dual-track shadow monitoring, the repo can also build:

```text
data/output/shadow_candidate_tracks/
  track_summary.csv
  official_baseline/
    release_index.csv
    <YYYY-MM-DD-mode>/
      live_pool.json
      live_pool_legacy.json
      release_manifest.json
  challenger_topk_60/
    release_index.csv
    <YYYY-MM-DD-mode>/
      live_pool.json
      live_pool_legacy.json
      release_manifest.json
```

Track metadata that downstream may rely on for shadow comparison:

- `profile`
- `source_track`
- `candidate_status`
- `version`
- `as_of_date`
- `activation_date`
- `pool_size`
- `expected_pool_size`

Baseline remains the official production reference. `challenger_topk_60` is shadow-only in this workflow.

## Recommended Downstream Read Priority

1. Read Firestore `strategy/CRYPTO_LEADER_ROTATION_LIVE_POOL`
2. If the latest Firestore payload is invalid or unavailable, prefer the downstream script's last known good upstream payload
3. If explicitly configured, read the synchronized `live_pool_legacy.json` or `live_pool.json`
4. If all upstream-aware layers fail, fall back to the downstream script's static universe as an emergency-only path

Freshness semantics:

- `as_of_date` is the monthly production snapshot date
- downstream should validate it against its own staleness threshold
- stale upstream data is a degraded state, not the same as a healthy fresh publish
- static fallback is a last resort and should be logged as degraded

## Downstream Pseudocode

```python
def load_trend_pool():
    payload = try_read_firestore("strategy", "CRYPTO_LEADER_ROTATION_LIVE_POOL")
    if is_valid_and_fresh(payload):
        return payload["symbol_map"], {"source": "fresh_upstream"}

    cached = read_last_known_good_upstream_payload()
    if cached:
        return cached["symbol_map"], {"source": "last_known_good", "degraded": True}

    legacy = try_read_local_json("live_pool_legacy.json")
    if is_valid_local_fallback(legacy):
        return legacy["symbol_map"], {"source": "local_file", "degraded": True}

    return STATIC_TREND_UNIVERSE, {"source": "static", "degraded": True}
```

## Rollback Strategy

Preferred rollback:

1. choose the previous version under `gs://<bucket>/crypto-leader-rotation/releases/`
2. copy its four artifacts back onto the `current/` prefix
3. update the Firestore summary document so `version`, `as_of_date`, and URIs point to that release

The downstream consumer contract does not need to change during rollback.
