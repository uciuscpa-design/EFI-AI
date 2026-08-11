# GEXY Decision Log

## 2026-08-10 — D001
**Decision:** Name the build `GEXY`.

**Reason:** The user selected GEXY as the project name.

## 2026-08-10 — D002
**Decision:** Build GEXY as a component of EFI-AI on a dedicated `feature/gexy` branch.

**Reason:** Preserve the existing EFI-AI codebase while isolating the new market-structure system during development.

## 2026-08-10 — D003
**Decision:** The UI must support both a candlestick overlay and a dedicated prediction chart.

**Reason:** The user wants predicted future movement visible directly against price action while also having a dedicated analytical view.

## 2026-08-10 — D004
**Decision:** Forecast horizons and chart windows must be adjustable.

**Reason:** Different intraday regimes require different observation and forecast horizons.

## 2026-08-10 — D005
**Decision:** GEXY will distinguish measured market data from inferred dealer positioning.

**Reason:** Public options data does not uniquely identify dealer inventory.

## 2026-08-10 — D006
**Decision:** Historical replay/backtesting is a first-class component, not a final afterthought.

**Reason:** The relationship between estimated hedge pressure and realized SPX movement must be empirically validated before relying on forecasts.
