from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd


DEFAULT_SIGNAL_COLUMNS = (
    "flow_contract_imbalance",
    "flow_premium_imbalance",
    "flow_net_signed_contracts",
    "flow_net_signed_premium_notional",
    "flow_signed_call_contracts",
    "flow_signed_put_contracts",
    "flow_signed_call_premium_notional",
    "flow_signed_put_premium_notional",
)


def _directional_accuracy(signal: np.ndarray, target: np.ndarray) -> float | None:
    mask = np.isfinite(signal) & np.isfinite(target) & (signal != 0) & (target != 0)
    if not mask.any():
        return None
    return float(np.mean(np.sign(signal[mask]) == np.sign(target[mask])))


def _spearman_rank_corr(x: pd.Series, y: pd.Series) -> float:
    """Compute Spearman correlation without requiring SciPy.

    Spearman correlation is Pearson correlation of the rank-transformed values.
    pandas' Series.corr(method="spearman") delegates to scipy.stats, which makes
    SciPy an unnecessary runtime dependency for this lightweight diagnostic.
    Average ranks preserve the standard tie-handling convention.
    """
    x_rank = x.rank(method="average")
    y_rank = y.rank(method="average")
    return float(x_rank.corr(y_rank, method="pearson"))


def _bucket_means(signal: pd.Series, target: pd.Series) -> tuple[float | None, float | None, int, int]:
    finite = pd.DataFrame({"signal": signal, "target": target}).replace([np.inf, -np.inf], np.nan).dropna()
    if len(finite) < 8 or finite["signal"].nunique() < 4:
        return None, None, 0, 0
    low_cut = float(finite["signal"].quantile(0.25))
    high_cut = float(finite["signal"].quantile(0.75))
    low = finite.loc[finite["signal"] <= low_cut, "target"]
    high = finite.loc[finite["signal"] >= high_cut, "target"]
    return (
        float(low.mean()) if len(low) else None,
        float(high.mean()) if len(high) else None,
        int(len(low)),
        int(len(high)),
    )


def score_flow_signals(
    frame: pd.DataFrame,
    *,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
    signal_columns: Iterable[str] = DEFAULT_SIGNAL_COLUMNS,
) -> pd.DataFrame:
    """Score exploratory one-day flow relationships without fitting a predictive model.

    Results are descriptive only. They report finite-sample Pearson/Spearman
    association, same-sign directional accuracy, and mean future return in the
    bottom/top signal quartiles. No parameter is learned and no result should be
    treated as validated until repeated out of sample across additional days.
    """
    working = frame.copy()
    if "replay_match" in working.columns:
        working = working.loc[working["replay_match"].fillna(False)].copy()

    rows: list[dict[str, object]] = []
    for raw_horizon in horizons_minutes:
        horizon = int(raw_horizon)
        target_column = f"forward_return_{horizon}m_bps"
        if target_column not in working.columns:
            continue
        target = pd.to_numeric(working[target_column], errors="coerce")

        for signal_column in signal_columns:
            if signal_column not in working.columns:
                continue
            signal = pd.to_numeric(working[signal_column], errors="coerce")
            finite_mask = np.isfinite(signal.to_numpy(dtype=float)) & np.isfinite(target.to_numpy(dtype=float))
            x = signal.loc[finite_mask]
            y = target.loc[finite_mask]
            n = int(len(x))
            if n < 3:
                pearson = float("nan")
                spearman = float("nan")
            else:
                pearson = float(x.corr(y, method="pearson"))
                spearman = _spearman_rank_corr(x, y)

            low_mean, high_mean, low_n, high_n = _bucket_means(x, y)
            direction = _directional_accuracy(
                x.to_numpy(dtype=float),
                y.to_numpy(dtype=float),
            )
            rows.append(
                {
                    "horizon_minutes": horizon,
                    "signal": signal_column,
                    "observations": n,
                    "pearson": pearson,
                    "spearman": spearman,
                    "directional_accuracy_same_sign": direction,
                    "bottom_quartile_mean_forward_bps": low_mean,
                    "top_quartile_mean_forward_bps": high_mean,
                    "bottom_quartile_rows": low_n,
                    "top_quartile_rows": high_n,
                    "top_minus_bottom_forward_bps": (
                        high_mean - low_mean
                        if high_mean is not None and low_mean is not None
                        else None
                    ),
                }
            )

    result = pd.DataFrame(rows)
    if result.empty:
        return result
    result["abs_spearman"] = pd.to_numeric(result["spearman"], errors="coerce").abs()
    return result.sort_values(
        ["horizon_minutes", "abs_spearman"],
        ascending=[True, False],
        na_position="last",
    ).reset_index(drop=True)
