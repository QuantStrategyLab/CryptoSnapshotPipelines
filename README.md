# crypto-leader-rotation

Language: English | [简体中文](README.zh-CN.md)

`crypto-leader-rotation` is a research-plus-production Python project whose only job is to provide a higher-quality Binance Spot mainstream-coin universe and leader candidate pool to a separate downstream strategy script.

This repository does not place trades and does not contain live execution logic. Its deliverable is a stable upstream selector that can export:

1. `data/output/latest_universe.json`
2. `data/output/latest_ranking.csv`
3. `data/output/live_pool.json`

## Current Status

The repository is now intentionally split into two tracks:

- `Production v1`
  - data source: `Binance Spot only`
  - universe mode: `core_major`
  - publish cadence: `monthly`
  - default outputs: `latest_universe.json`, `latest_ranking.csv`, `live_pool.json`, `live_pool_legacy.json`
- `Experimental external-data track`
  - used for research, comparison, and validation only
  - not enabled by default
  - not part of the default production publish path

Production v1 is the frozen default path for this repository. The external-data branch stays in the repo, but it is explicitly experimental until it proves stably better than Binance-only across the key walk-forward leader-selection metrics.

The design target is practical rather than flashy:

- use only data visible at the time
- stay inside Binance Spot daily OHLCV
- identify coins that are more likely to become 30/60/90-day stage leaders
- maximize leader capture, precision, recall, and ranking quality
- reduce false positives, turnover noise, and overfitting
- keep outputs stable, explainable, and easy to integrate

## Why This Project Exists

Most trading systems blur together three different problems:

1. universe construction
2. leader identification and ranking
3. order execution

This project focuses only on the first two. It is meant to sit upstream of another quant script and answer a narrower question:

At each rebalance date, using only then-visible Binance Spot daily data, which liquid mainstream coins should even be considered by the downstream strategy, and which of them currently rank highest as likely future leaders?

That makes this repository a better fit as a production upstream selector than a monolithic trading bot:

- it is easier to explain and audit
- it is easier to backtest with strict walk-forward logic
- it is easier to swap into another strategy stack
- it avoids coupling model research to execution plumbing

## Why Not Deep Learning

With only Binance Spot daily OHLCV, deep learning is usually the wrong first move:

- signal-to-noise is limited
- sample size is small relative to model capacity
- interpretability gets worse
- overfitting risk rises quickly
- walk-forward robustness usually suffers

For this data regime, the strongest practical approach is:

`hard universe filter + robust feature library + rule baseline + light ML + regime-aware blending + walk-forward validation`

That is exactly what this repository implements.

## Data Source

Only Binance Spot public data is used in the current version:

- `exchangeInfo`
- symbol metadata
- daily klines
- local CSV cache
- incremental updates
- one raw file per symbol

No market cap, on-chain, funding, sentiment, or third-party datasets are used yet.

## Repository Structure

```text
crypto-leader-rotation/
  .github/
    workflows/
      monthly_publish.yml
  README.md
  requirements.txt
  .gitignore
  config/
    default.yaml
  docs/
    integration_contract.md
    external_data_roadmap.md
    validation_status.md
  data/
    raw/
    cache/
    processed/
    models/
    reports/
    output/
  notebooks/
    research_notes.md
  scripts/
    download_history.py
    build_live_pool.py
    publish_release.py
    write_release_heartbeat.py
    validate_external_data.py
    run_research_backtest.py
    run_walkforward_validation.py
    debug_single_date_snapshot.py
  src/
    __init__.py
    config.py
    utils.py
    binance_client.py
    universe.py
    indicators.py
    features.py
    labels.py
    rules.py
    regime.py
    models.py
    ranking.py
    portfolio.py
    backtest.py
    evaluation.py
    export.py
    plots.py
    pipeline.py
```

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

For reproducible research and validation in this repository, prefer invoking the environment directly with `.venv/bin/python ...`.

Methodology note:

- the intended validation environment is `.venv/bin/python`
- plain `python3` in this workspace may not have `scikit-learn` or a usable `lightgbm`
- if that happens, the code can silently fall back to weaker backends and produce non-comparable metrics

If `lightgbm` is not available in your environment, the code automatically falls back to:

- `HistGradientBoostingRegressor`
- `RandomForestRegressor`
- ridge-style fallback if needed

The default code path is still LightGBM-first.

## Configuration

All important parameters live in `config/default.yaml`, including:

- data directories and date range
- universe filtering thresholds
- rebalance settings
- walk-forward windows
- label horizons and `future_top_k`
- rule ranking schemes
- regime-specific ensemble weights
- ML backend settings
- export settings
- publish settings for GCS / Firestore release

This keeps the project easy to tune without scattering magic numbers across files.

## Download Historical Data

Full download/update:

```bash
.venv/bin/python scripts/download_history.py
```

Quick smoke test with a smaller set:

```bash
.venv/bin/python scripts/download_history.py --limit 20
```

Specific symbols:

```bash
.venv/bin/python scripts/download_history.py --symbols BTCUSDT ETHUSDT SOLUSDT XRPUSDT
```

The downloader:

- refreshes `exchangeInfo`
- saves symbol metadata into `data/cache/symbol_metadata.csv`
- saves one CSV per symbol under `data/raw/`
- supports incremental daily updates

## Release Contract Smoke Check

Validate the local production artifacts before publish or rollback:

```bash
.venv/bin/python scripts/validate_release_contract.py --mode core_major --expected-pool-size 5
```

Require a generated manifest as part of the check:

```bash
.venv/bin/python scripts/validate_release_contract.py --mode core_major --expected-pool-size 5 --require-manifest
```

## Minimal Runnable Flow

1. Download data

```bash
.venv/bin/python scripts/download_history.py --limit 30
```

2. Run research/backtest

```bash
.venv/bin/python scripts/run_research_backtest.py
```

3. Run walk-forward validation

```bash
.venv/bin/python scripts/run_walkforward_validation.py
```

4. Build live exports for the downstream strategy

```bash
.venv/bin/python scripts/build_live_pool.py
```

5. Prepare a monthly release payload

```bash
.venv/bin/python scripts/publish_release.py --dry-run
```

6. Debug one historical date if needed

```bash
.venv/bin/python scripts/debug_single_date_snapshot.py 2024-03-31
```

7. Build a local monthly shadow release history for downstream replay

```bash
.venv/bin/python scripts/build_shadow_release_history.py --include-selection-meta
```

8. Build the dual-track shadow candidate release histories

```bash
.venv/bin/python scripts/build_shadow_candidate_tracks.py
```

9. Run the monthly official + shadow build wrapper

```bash
.venv/bin/python scripts/run_monthly_shadow_build.py
```

Or, with the local helper target:

```bash
make monthly-shadow-build
```

## Recommended Validation Baseline

The recommended research baseline is now:

- purged walk-forward validation
- configurable overlap aggregation, with `mean` kept as the default historical bridge and `latest` available as a stricter realism check
- additive monthly live-pool shadow validation aligned to the exported `live_pool.json` artifact

Methodology hardening note:

- older walk-forward reports in this repository were generated before train-tail purging was added
- those legacy runs could let training rows near the boundary use forward labels whose price window extended into the next test segment
- older reports also averaged duplicate predictions from overlapping test windows, which is smoother than the real live path
- those older optimistic metrics should be treated as historical / legacy and are not directly comparable to the hardened baseline

## Downstream Live-Pool Contract

The stable downstream contract is the exported monthly live pool, not the research reports.

Downstream consumers should rely on these core fields in `data/output/live_pool.json`, `data/output/live_pool_legacy.json`, or the Firestore summary document:

- `as_of_date`
- `version`
- `mode`
- `pool_size`
- `symbols`
- `symbol_map`
- `source_project`

Publish-time pointer fields such as `storage_prefix`, `current_prefix`, `live_pool_uri`, `live_pool_legacy_uri`, `latest_universe_uri`, and `latest_ranking_uri` are stable when present in the published Firestore payload, but they are release/distribution metadata rather than research features.

Optional additive research extensions:

- `selection_meta` may be present in shadow-release artifacts or in live exports if explicitly enabled
- these fields are useful for downstream replay experiments such as mild sizing tilts
- they are not part of the minimum stable contract and should be treated as optional

Freshness guidance:

- production v1 publishes a monthly `core_major` pool
- downstream should treat `as_of_date` as the snapshot date to validate freshness against its own staleness threshold
- stale or invalid upstream data should be handled as a degraded state, not treated as equivalent to a healthy fresh publish

See `docs/integration_contract.md` for the full contract and fallback semantics.

## Shadow Replay Support

For end-to-end local replay, this repository can now build a versioned monthly shadow release history under `data/output/shadow_releases/`.

Each shadow release contains:

- `live_pool.json`
- `live_pool_legacy.json`
- `release_manifest.json`

The root also contains `release_index.csv`, which downstream replay tools can use to step through historical monthly upstream artifacts with a configurable activation lag and without live Firestore/GCS dependencies.

When available, each release index row also carries the upstream `regime` and `regime_confidence` for that monthly snapshot. These are research diagnostics for robustness slicing, not part of the minimum downstream contract.

## Shadow Candidate Track

Baseline remains the official production reference.

`challenger_topk_60` is now maintained only as an additive shadow-production candidate under `data/output/shadow_candidate_tracks/`.

The current dual-track convention is:

- `official_baseline`
  - profile: `baseline_blended_rank`
  - source track: `official_baseline`
  - candidate status: `official_reference`
- `challenger_topk_60`
  - profile: `challenger_topk_60`
  - source track: `shadow_candidate`
  - candidate status: `shadow_candidate`

These shadow candidate artifacts are versioned local release histories for downstream comparison and paper monitoring. They do not replace `data/output/live_pool.json`, do not alter the publish default, and do not imply a live switch.

## Monthly Shadow Build

The monthly operator workflow is now:

1. build the official baseline live artifacts
2. run the baseline publish dry-run check
3. refresh the dual-track shadow candidate histories

Canonical command:

```bash
.venv/bin/python scripts/run_monthly_shadow_build.py
```

Local helper target:

```bash
make monthly-shadow-build
```

Canonical outputs:

- official baseline
  - `data/output/live_pool.json`
  - `data/output/live_pool_legacy.json`
  - `data/output/release_manifest.json` from the dry-run publish check
- shadow candidate tracks
  - `data/output/shadow_candidate_tracks/track_summary.csv`
  - `data/output/shadow_candidate_tracks/official_baseline/release_index.csv`
  - `data/output/shadow_candidate_tracks/challenger_topk_60/release_index.csv`
  - `data/output/monthly_shadow_build_summary.json`

Track identity fields to rely on:

- `profile`
- `source_track`
- `candidate_status`
- `version`
- `as_of_date`
- `activation_date`
- `expected_pool_size`

Baseline remains the official production reference. `challenger_topk_60` remains shadow-only.

## Monthly Build Telegram Notify

Optional short build/publish health notification:

```bash
.venv/bin/python scripts/run_monthly_build_telegram.py
```

Or:

```bash
make monthly-build-telegram
```

Environment:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

Behavior:

- sends only a short operational summary for monthly build/publish health
- uses existing monthly build outputs such as `monthly_shadow_build_summary.json`, `live_pool.json`, `release_manifest.json`, and `shadow_candidate_tracks/track_summary.csv`
- skips cleanly if Telegram credentials are missing
- never changes the monthly build behavior and is not a review-package generator

## Monthly Review Package

Optional reporting-only review package:

```bash
.venv/bin/python scripts/run_monthly_review_briefing.py
```

Or:

```bash
make monthly-review-briefing
```

Outputs:

- `data/output/monthly_review.md`
- `data/output/monthly_review.json`
- `data/output/monthly_review_prompt.md`

Behavior:

- uses only upstream monthly build outputs
- summarizes official baseline release status, publish manifest status, and shadow track coverage
- emits warnings when monthly artifacts do not align on `as_of_date`, `version`, or `mode`
- produces a structured review prompt/checklist for manual follow-up
- is reporting-only and does not alter monthly build behavior

## Dynamic Universe Logic

The universe is a hard filter layer, not the final holdings set.

At each history point, only then-visible data is used to decide whether a symbol can enter the candidate universe.

Base filters:

- `status == TRADING`
- `quoteAsset == USDT`
- `isSpotTradingAllowed == True`

Explicit exclusions:

- `BTCUSDT`
- `BNBUSDT`
- stablecoin-related assets such as `USDC`, `FDUSD`, `TUSD`, `USDP`, `DAI`, `PAX`
- leveraged/directional tokens such as `UP`, `DOWN`, `BULL`, `BEAR`

History and liquidity filters:

- minimum listing age
- 30/90/180-day average quote volume thresholds
- liquidity stability threshold
- tradable-day ratio threshold

Universe refresh frequency defaults to monthly. A monthly snapshot is formed using only data available on that snapshot date, then held until the next universe refresh.

## Feature Library

The feature library is intentionally broad but still practical.

### Relative-to-BTC strength

- `roc20`, `roc60`, `roc120`
- `rs20`, `rs60`, `rs120`
- `rs_combo`
- `rs_risk_adj`

### Absolute trend quality

- `sma20`, `sma60`, `sma120`, `sma200`
- `price_vs_sma20`, `price_vs_sma60`, `price_vs_sma120`, `price_vs_sma200`
- `trend_persist_90`
- `ma200_slope`
- `dist_to_90d_high`
- `dist_to_180d_high`
- `breakout_proximity`

### Risk-adjusted momentum and drawdown

- `vol20`, `vol60`
- `momentum_combo`
- `risk_adjusted_momentum`
- `downside_volatility`
- `atr14`, `atr_ratio`
- `rolling_drawdown`
- `ulcer_index`
- `drawdown_severity`

### Liquidity and tradability

- `quote_volume`
- `avg_quote_vol_30`, `avg_quote_vol_90`, `avg_quote_vol_180`
- `liquidity_stability`
- `age_days`
- `tradable_ratio_180`
- `recent_liquidity_acceleration`

### BTC and market environment

- `btc_above_ma200`
- `btc_ma200_slope`
- `btc_zscore_120`
- `breadth_above_sma60`
- `breadth_above_sma200`
- `universe_momentum_dispersion`
- `universe_rs_dispersion`
- `single_leader_burst`

### Optional enhancements already included

- `rolling_beta_to_btc`
- `rolling_corr_to_btc`

## Labels

The models do not try to predict price directly. They predict leader-quality targets.

Implemented labels:

- `future_return_30`
- `future_return_60`
- `future_return_90`
- `future_rank_pct_30`
- `future_rank_pct_60`
- `future_rank_pct_90`
- `future_topk_label_30`
- `future_topk_label_60`
- `future_topk_label_90`
- `blended_target`

`blended_target` is the default training target and blends future cross-sectional rank percentiles across multiple horizons.

## Rule Scores, ML, and Regime Blending

Three rule schemes are implemented:

- `relative_strength_focus`
- `balanced_leader`
- `conservative_trend_quality`

Each rule scheme:

- cross-sectionally rank-normalizes features
- applies config-driven weights
- outputs a usable rule-only baseline

Models:

- linear baseline: ridge or elastic net
- main model: LightGBM regressor when available
- automatic fallback if LightGBM is unavailable

Regime classifier:

- `risk_off`
- `btc_dominant`
- `broad_alt_strength`
- `late_momentum`

The final ensemble score blends:

- `rule_score`
- `linear_score`
- `ml_score`

using either default weights or regime-specific weights from `config/default.yaml`.

## Walk-Forward Validation

This repository does not train on the full sample and then look backward.

The recommended validation loop is rolling, purged at the train/test boundary, and out-of-sample:

- rolling train window
- rolling test window
- forward step
- train-tail purge sized from the label horizons by default
- signal formed on day `t`
- portfolio executed on day `t+1`
- daily PnL approximated with open-to-open returns
- overlapping-window prediction aggregation configurable as `mean` or `latest`

Default settings:

- train window: 720 days
- test window: 120 days
- step: 60 days
- purge: max configured label horizon unless overridden
- overlap aggregation: `mean`
- rebalance: weekly
- top N: 3

Run it with:

```bash
.venv/bin/python scripts/run_walkforward_validation.py
```

Legacy comparison note:

- historical walk-forward summaries produced before this hardening pass may look better because they did not purge train tails and they averaged overlapping test-window predictions by default
- those historical metrics are useful as archive context only and should not be used as the recommended baseline going forward

Outputs include:

- `data/reports/walkforward_windows.csv`
- `data/reports/walkforward_validation_summary.csv`
- `data/reports/monthly_live_pool_shadow_detail.csv`
- `data/reports/monthly_live_pool_shadow_summary.csv`
- `data/reports/performance_summary.csv`
- `data/reports/leader_metrics.csv`
- `data/reports/equity_curves.png`
- `data/reports/leader_metrics.png`

## Evaluation Focus

Standard strategy metrics:

- CAGR
- Annualized Volatility
- Sharpe
- Sortino
- Max Drawdown
- Calmar
- Win Rate
- Turnover

Leader-selection metrics:

- Precision@N
- Recall@N
- Overlap Hit Rate
- Average Rank of Future Top Performers
- Leader Capture Rate

When comparing models, prefer:

- out-of-sample leader capture
- out-of-sample precision/recall
- robustness across windows
- turnover control

over raw CAGR alone.

## Live Output Files

This is the most important delivery of the project.

### 1. `data/output/latest_universe.json`

Illustrative abbreviated universe snapshot example:

```json
{
  "as_of_date": "2026-03-13",
  "symbols": ["ETHUSDT", "SOLUSDT", "XRPUSDT"]
}
```

This is a research/universe snapshot example, not the official downstream live-pool contract. The official exported pool for downstream consumers is `data/output/live_pool.json` / `data/output/live_pool_legacy.json`, and its exact field semantics are defined in `docs/integration_contract.md`.

### 2. `data/output/latest_ranking.csv`

Contains at least:

- `as_of_date`
- `symbol`
- `rule_score`
- `linear_score`
- `ml_score`
- `final_score`
- `regime`
- `confidence`
- `selected_flag`

### 3. `data/output/live_pool.json`

The default live export contains both a simple list and a mapping payload:

```json
{
  "as_of_date": "2026-03-13",
  "pool_size": 5,
  "symbols": ["TRXUSDT", "ETHUSDT", "BCHUSDT", "NEARUSDT", "LTCUSDT"],
  "symbol_map": {
    "TRXUSDT": {"base_asset": "TRX"},
    "ETHUSDT": {"base_asset": "ETH"},
    "BCHUSDT": {"base_asset": "BCH"},
    "NEARUSDT": {"base_asset": "NEAR"},
    "LTCUSDT": {"base_asset": "LTC"}
  }
}
```

Here `pool_size` and `symbols` refer to the full official exported live pool for that snapshot. Downstream display panels or local candidate rankings are separate downstream concepts.

For older scripts that expect the mapping to sit directly under the `symbols` key, the exporter also writes:

- `data/output/live_pool_legacy.json`

Run the live builder with:

```bash
.venv/bin/python scripts/build_live_pool.py
```

You can also build a historical live snapshot:

```bash
.venv/bin/python scripts/build_live_pool.py --as-of-date 2024-03-31
```

The production monthly release path defaults to the stricter `core_major` universe mode. Research and walk-forward validation continue to use `broad_liquid`.

Production defaults today are:

- `external_data.enabled: false`
- `universe.live_mode: core_major`
- `release.channel: production`
- `release.production_profile: binance_only_core_major_monthly`

So running `.venv/bin/python scripts/build_live_pool.py` with no extra flags builds the frozen Production v1 path, not the experimental external-data path.

## Monthly Publish Chain

This repository can now act as a monthly upstream publisher for downstream strategy systems.

The default monthly publisher is Production v1:

- `Binance Spot only`
- `core_major`
- `external_data.enabled = false`

Operational note:

- the monthly workflow is intended to run on a `self-hosted` GitHub Actions runner
- reason: GitHub-hosted runners can be blocked by Binance with `451` responses on `api.binance.com`
- the self-hosted runner should have stable outbound access to Binance Spot public APIs

The experimental external-data track is not part of the default publish path.

The monthly chain is intentionally lightweight:

1. update/download Binance Spot history
2. build the production `core_major` live outputs
3. publish those files to GCS
4. write a lightweight Firestore summary document

The publish script reads these local artifacts:

- `data/output/latest_universe.json`
- `data/output/latest_ranking.csv`
- `data/output/live_pool.json`
- `data/output/live_pool_legacy.json`

Run a local dry-run:

```bash
PUBLISH_ENABLED=false \
GCP_PROJECT_ID=demo-project \
GCS_BUCKET=demo-bucket \
python scripts/publish_release.py --dry-run
```

The expected production sequence is:

```bash
python scripts/build_live_pool.py
python scripts/publish_release.py --dry-run
```

If you want to test experimental external-data behavior, that must be enabled explicitly in a non-default research flow. It is not used by the monthly production workflow.

### Versioning

Each release uses an explicit rollback-friendly version:

- `YYYY-MM-DD-core_major`

Example:

- `2026-03-13-core_major`

### GCS Layout

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

### Firestore Summary Document

Default location:

- collection: `strategy`
- document: `CRYPTO_LEADER_ROTATION_LIVE_POOL`

Fields include:

- `as_of_date`
- `mode`
- `version`
- `pool_size`
- `symbols`
- `symbol_map`
- `storage_prefix`
- `live_pool_legacy_uri`
- `generated_at`
- `source_project`

The document is intentionally small. The full ranking CSV remains in GCS instead of Firestore.

### Recommended Downstream Read Priority

Documentation-only contract for downstream consumers:

1. read Firestore `strategy/CRYPTO_LEADER_ROTATION_LIVE_POOL`
2. if Firestore is unavailable, read `live_pool_legacy.json`
3. if both fail, fall back to a static local universe

See [docs/integration_contract.md](/Users/lisiyi/Projects/CryptoLeaderRotation/docs/integration_contract.md) for the precise payload contract and pseudocode.

### Manual Trigger And Rollback

Manual GitHub Actions trigger:

- open the `Monthly Publish` workflow
- run `workflow_dispatch`

Rollback plan:

1. choose an earlier version under `releases/<YYYY-MM-DD-mode>/`
2. copy its artifacts back to the `current/` prefix
3. update the Firestore summary document so it points to that version

### GitHub Actions Secrets And Vars

GitHub Actions secrets and variables are not created by this repository. They must be configured by the repository owner in GitHub settings, or created with the GitHub CLI, and are only referenced from workflows.

This workflow currently reads:

From `secrets.*`:

- `GCP_SERVICE_ACCOUNT_KEY`
- `GCP_PROJECT_ID`
- `GCS_BUCKET`

From `vars.*`:

- `PUBLISH_ENABLED`
- `PUBLISH_MODE`
- `DOWNLOAD_TOP_LIQUID`
- `FIRESTORE_COLLECTION`
- `FIRESTORE_DOCUMENT`

Practical setup paths:

1. GitHub repository UI
   - `Settings -> Secrets and variables -> Actions`
2. GitHub CLI
   - `gh secret set ...`
   - `gh variable set ...`

The workflow uses `secrets.*` for credentials and sensitive deployment parameters, and `vars.*` for non-secret operational toggles.

Recommended first setup:

```bash
gh secret set GCP_SERVICE_ACCOUNT_KEY < gcp-service-account.json
gh secret set GCP_PROJECT_ID --body "your-gcp-project"
gh secret set GCS_BUCKET --body "your-release-bucket"

gh variable set PUBLISH_ENABLED --body "true"
gh variable set PUBLISH_MODE --body "core_major"
gh variable set DOWNLOAD_TOP_LIQUID --body "90"
gh variable set FIRESTORE_COLLECTION --body "strategy"
gh variable set FIRESTORE_DOCUMENT --body "CRYPTO_LEADER_ROTATION_LIVE_POOL"
```

### Logs Branch Heartbeat

After a successful monthly publish, the workflow writes one small heartbeat JSON file to the `logs` branch:

```text
monthly/<YYYY-MM-DD-mode>.json
```

Example:

```text
monthly/2026-03-13-core_major.json
```

The heartbeat contains:

- `version`
- `as_of_date`
- `mode`
- `pool_size`
- `symbols`
- `storage_prefix`
- `generated_at`
- `workflow_run_id`
- `workflow_run_url`

The main workflow does not trigger on `push`, only on `schedule` and `workflow_dispatch`, so pushing to the `logs` branch does not create a publish loop. The job also explicitly skips execution when `github.ref_name == 'logs'`.

You can generate the heartbeat payload locally without pushing:

```bash
python scripts/write_release_heartbeat.py --manifest data/output/release_manifest.json --output-dir data/output/heartbeat
```

## External Data Roadmap

The Binance-only version is a strong practical baseline, but it is not the final form of the project.

Important production note:

- the external-data code path remains available for controlled experimentation
- it is not enabled by default
- it does not participate in `Production v1`
- it will only be promoted if future validation shows stable superiority over Binance-only

The first external-data priority is not sentiment or on-chain complexity. It is:

1. extending pre-Binance daily history where Binance starts too late
2. supplementing alternate-exchange daily history when Binance history is incomplete
3. optionally introducing market-cap metadata later for cleaner large-cap production filtering

Preparation added in this repository:

- [src/external_data.py](/Users/lisiyi/Projects/CryptoLeaderRotation/src/external_data.py)
- [scripts/validate_external_data.py](/Users/lisiyi/Projects/CryptoLeaderRotation/scripts/validate_external_data.py)
- [docs/external_data_roadmap.md](/Users/lisiyi/Projects/CryptoLeaderRotation/docs/external_data_roadmap.md)

The current merge policy is:

- prefer `binance` on overlapping dates
- fill earlier history from `pre_binance`
- allow `alternate_exchange` to fill missing dates if configured
- sort by date, enforce monotonic time, and keep source labels on each row

Local validation of the merge logic:

```bash
.venv/bin/python scripts/validate_external_data.py
```

## Validation Status

The current validation snapshot and remaining release blockers are tracked in:

- [docs/validation_status.md](/Users/lisiyi/Projects/CryptoLeaderRotation/docs/validation_status.md)

That document summarizes:

- current research and walk-forward baseline status
- publish-chain validation already completed
- external-data preparation status
- remaining production checks
- non-blocking optimization items that are still intentionally deferred

## Single-Date Debugging

To inspect one historical date:

```bash
.venv/bin/python scripts/debug_single_date_snapshot.py 2024-03-31
```

This exports a detailed snapshot file into `data/output/` containing:

- universe membership
- feature values
- rule score
- linear score
- ML score
- final score
- regime
- confidence

## How Future Leakage Is Avoided

This repository is built around point-in-time discipline:

- universe eligibility uses only current and past history
- universe refresh happens on the snapshot date only
- features use rolling windows over current and past data only
- labels are created separately and used only for training/evaluation
- the recommended purged walk-forward path excludes train-tail rows whose forward labels would extend past the train boundary
- the live builder trains only on dates whose forward labels are already fully known
- portfolio signals are formed on `t` and executed on `t+1`

## Known Limitations

1. Survivorship bias

Current Binance metadata comes from the present-day exchange listing, so delisted names are not fully represented.

2. Listing bias

A coin that later became important may not have enough early history to pass the filters immediately.

3. Binance-only limitation

This version sees only Binance Spot daily activity. It does not see the broader market.

4. Missing data families

No market cap, on-chain, derivatives, funding, order-book, or sentiment features are included yet.

5. Daily-bar limitation

Execution is approximated with next-day open-to-open returns, not intraday fills.

## Future Extensions

- add market cap and circulating supply inputs
- add on-chain activity and exchange flow data
- add perpetual funding and basis features
- add social or narrative proxies
- add symbol delisting archives to reduce survivorship bias
- add model persistence and scheduled batch jobs
- add richer calibration and confidence diagnostics

## Recommended Usage Pattern

Treat this repository as a reusable upstream selector.

The downstream trading script should ideally:

1. read `data/output/live_pool.json`
2. optionally read `data/output/latest_ranking.csv`
3. apply its own execution and position sizing rules
4. remain decoupled from the leader-selection research stack

That separation is the main reason this project exists.
