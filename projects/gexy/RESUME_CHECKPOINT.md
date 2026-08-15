# GEXY — Durable Resume Checkpoint

**Checkpoint date:** 2026-08-14
**Branch:** `feature/gexy`
**Repository:** `uciuscpa-design/EFI-AI`

## Resume protocol

When Shannon says **`resume gexy`**, treat this file and `projects/gexy/PROJECT_RECORD.md` as the durable source of truth and continue from the latest unfinished action without asking Shannon to reconstruct prior sessions.

Standing working preference: proceed continuously with the safest recommended GEXY engineering/research steps unless a real external credential, purchase, account action, or other user-only action is required. Preserve all significant decisions and results in the project record/Git history.

## Current project state

GEXY is a real-time SPX options GEX/GAX/hedge-prediction research engine with configurable forecast horizons, candlestick overlays, separate forecast visualization, historical backtesting, real-time market data, and leakage-safe validation.

Production direction logic is unchanged. Production confidence is unchanged. Execution is disabled. Research/shadow mode only.

Public data does not reveal the true dealer book. Never fabricate dealer identity/positioning, IV, Greeks, gamma flip, ES data, or other missing provider fields.

## Frozen research status

### H5 direction hypothesis
- ID: `GEXY-H5-SLOPE-INVERT-v1`
- Regime: `negative_gamma_acceleration`
- Horizon: 5 minutes only
- Rule: local GEX slope > 0 => down; slope < 0 => up; zero/missing => unscored
- Selection session: 2026-08-14; it is excluded from independent validation
- Promotion research gate: at least 2 later independent informative sessions with positive lift versus each session's always-down baseline, plus positive aggregate lift
- No retuning during forward validation

### Confidence calibration
- ID: `GEXY-CONFIDENCE-CAL-v1`
- Artifact: `projects/gexy/research/CONFIDENCE_CALIBRATION_V1_MODEL.json`
- Frozen fingerprint: `24b38617e061c18a864c3c871c863504e10a3c146eb81d3c7f4cded93b81cab0`
- Research-only estimate of P(current predicted direction is correct)
- Drift guard blocks scoring if the frozen selection fit changes
- Multiple independent sessions are required before any shadow-model promotion review

### Selection-session diagnostic
- 12,420 shadow rows
- 9,140 resolved
- 3,280 unresolved
- Current first-pass predictor directional accuracy about 52.17%
- Always-down baseline about 73.84%
- Predicted-up branch is the dominant wrong-sign failure mode
- Current raw production confidence is mechanically saturated and is not a calibrated probability

## Windows session collector

Self-hosted Windows runner: `gexy-windows` on machine `THANKYOU`.

Scheduled task: `GEXY Session Collector`
- Weekdays around 6:20 AM Pacific
- Last verified state: `Ready`
- Last result: `0`
- Next scheduled session: Monday 2026-08-17 around 6:20 AM PDT

Monday's independent session must remain untouched by weekend retuning. After the session, evaluate the exact frozen H5 and confidence-calibration models separately.

## SPX/ES point-in-time infrastructure

Built and tested:
- Exact source-time provenance for the selected SPX call/put parity pair
- Safe synthetic-SPX anchor is the later timestamp of the required source quotes
- Provider-neutral `MarketObservation`
- Frozen 5-second maximum reference lag
- No future nearest-neighbor matching
- Stale/missing references are unscoreable
- Raw provider nanosecond timestamps remain authoritative
- A reference just +1 ns after the SPX anchor is rejected
- Append-only synchronization journal and integrity/coverage reporting
- Full Windows Python suite at latest tested checkpoint: 232 passed, 1 unrelated warning

SPY must never be substituted for or described as ES futures.

## Databento decision

Preferred v1 ES research provider: **Databento**. Massive remains a fallback.

Frozen first research shape:
- Dataset: `GLBX.MDP3`
- Schema: `trades`
- Continuous selector: `ES.v.0`
- `stype_in=continuous`
- Persist the actual mapped raw futures contract symbol and instrument ID in addition to the continuous selector
- Preserve raw `ts_event_ns` and `ts_recv_ns`
- No ES-derived production feature until a separately versioned hypothesis passes chronological validation

Existing GEXY Databento scaffolding:
- `packages/gexy/databento_es.py`
- `packages/gexy/databento_preflight.py`
- `scripts/gexy_databento_preflight.py`
- `.github/workflows/gexy-databento-preflight.yml`
- `.env.example` includes a blank `DATABENTO_API_KEY=` placeholder

Last Databento preflight:
- status: `not_configured`
- API key absent
- Databento Python client absent
- no network attempted
- no secret exposed
- production/execution remain disabled

## EXACT CURRENT USER STEP — resume here

Shannon asked for **baby steps for Databento**.

Current baby step is **Step 1 only**:
1. Go to Databento and create an account or sign in.
2. Open the API Keys section.
3. Use the existing API key or create a dedicated key named `GEXY`.
4. DO NOT paste the key into ChatGPT.
5. DO NOT commit the key to GitHub.
6. When the key is visible/ready, Shannon should say only: **`I see the key`** or **`Databento key ready`**.

### Next baby step after Shannon says the key is ready
Give Step 2 only: safely place the key in the local Windows file:

`C:\Users\shannon\Documents\EFI-AI\.env`

as:

`DATABENTO_API_KEY=<private value>`

Do not ask Shannon to paste the value into chat.

After that, proceed one baby step at a time:
1. Verify the environment variable is detected without displaying its value.
2. Install the official Databento Python client if still absent.
3. Run the existing no-secret GEXY Databento preflight.
4. Run a read-only connectivity/symbol-mapping test.
5. First use real historical ES data to validate the synchronization pipeline before paying for/depending on live ES access.
6. Collect SPX/ES synchronization-only rows and require zero lookahead violations.
7. Only then define a separately versioned ES predictive hypothesis.

## Safety boundary

Do not merge to main while the model remains unvalidated. Do not enable execution. Do not change frozen H5 or confidence-calibration artifacts during independent forward validation. Do not spend money on a live data plan merely to advance the build if historical data can validate the pipeline first.

## Resume instruction to assistant

If a future chat begins with **`resume gexy`**:
1. Retrieve/read this resume checkpoint and the canonical project record.
2. Check for any newer GEXY checkpoint or commits and prefer the newest state if one exists.
3. State the current position in a few lines.
4. Continue immediately from the first unfinished step.
5. Do not make Shannon repeat completed setup or project history.
