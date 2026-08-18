from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_incremental import partial_spearman
from packages.gexy.tradeflow_hedge_robustness import matched_with_coverage


HEDGE_SIGNAL = "hedge_delta_units"
RAW_SIGNAL = "flow_net_signed_contracts"
MOMENTUM_SIGNAL = "backward_return_1m_bps"
DEFAULT_HORIZONS = (5, 15)


def _spearman(x: pd.Series, y: pd.Series) -> tuple[int, float]:
    frame = pd.DataFrame(
        {
            "x": pd.to_numeric(x, errors="coerce"),
            "y": pd.to_numeric(y, errors="coerce"),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    n = len(frame)
    if n < 3:
        return n, float("nan")
    return n, float(
        frame["x"].rank(method="average").corr(
            frame["y"].rank(method="average"), method="pearson"
        )
    )


def score_control_structure(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    trading_day: str,
    horizons_minutes: Iterable[int] = DEFAULT_HORIZONS,
    min_volume_coverage: float = 0.90,
) -> pd.DataFrame:
    """Audit how fixed controls change the net-delta/forward-return association."""
    sample = matched_with_coverage(raw, hedge, min_volume_coverage=min_volume_coverage)
    required_base = {HEDGE_SIGNAL, RAW_SIGNAL, MOMENTUM_SIGNAL}
    missing = sorted(required_base.difference(sample.columns))
    if missing:
        raise ValueError(f"matched frame missing required columns: {', '.join(missing)}")

    rows: list[dict[str, object]] = []
    for raw_horizon in horizons_minutes:
        horizon = int(raw_horizon)
        target_column = f"forward_return_{horizon}m_bps"
        if target_column not in sample.columns:
            continue
        target = sample[target_column]

        n_hedge, hedge_target = _spearman(sample[HEDGE_SIGNAL], target)
        n_raw, raw_target = _spearman(sample[RAW_SIGNAL], target)
        n_momentum, momentum_target = _spearman(sample[MOMENTUM_SIGNAL], target)
        _, hedge_raw = _spearman(sample[HEDGE_SIGNAL], sample[RAW_SIGNAL])
        _, hedge_momentum = _spearman(sample[HEDGE_SIGNAL], sample[MOMENTUM_SIGNAL])
        _, raw_momentum = _spearman(sample[RAW_SIGNAL], sample[MOMENTUM_SIGNAL])

        n_mom, partial_momentum = partial_spearman(
            sample[HEDGE_SIGNAL], target, sample[[MOMENTUM_SIGNAL]]
        )
        n_raw_only, partial_raw = partial_spearman(
            sample[HEDGE_SIGNAL], target, sample[[RAW_SIGNAL]]
        )
        n_both, partial_both = partial_spearman(
            sample[HEDGE_SIGNAL], target, sample[[MOMENTUM_SIGNAL, RAW_SIGNAL]]
        )

        ordinary_sign = np.sign(hedge_target) if np.isfinite(hedge_target) else np.nan
        both_sign = np.sign(partial_both) if np.isfinite(partial_both) else np.nan
        sign_flip = bool(
            np.isfinite(ordinary_sign)
            and np.isfinite(both_sign)
            and ordinary_sign != 0
            and both_sign != 0
            and ordinary_sign != both_sign
        )

        rows.append(
            {
                "trading_day": str(trading_day),
                "horizon_minutes": horizon,
                "observations": int(min(n_hedge, n_raw, n_momentum, n_mom, n_raw_only, n_both)),
                "hedge_target_spearman": hedge_target,
                "raw_target_spearman": raw_target,
                "momentum_target_spearman": momentum_target,
                "hedge_raw_spearman": hedge_raw,
                "hedge_momentum_spearman": hedge_momentum,
                "raw_momentum_spearman": raw_momentum,
                "hedge_partial_controlling_momentum": partial_momentum,
                "hedge_partial_controlling_raw": partial_raw,
                "hedge_partial_controlling_momentum_and_raw": partial_both,
                "ordinary_to_both_sign_flip": sign_flip,
            }
        )

    return pd.DataFrame(rows)
