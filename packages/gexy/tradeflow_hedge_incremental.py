from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_robustness import CORE_SIGNAL_PAIRS, matched_with_coverage


def _rank_residual(series: pd.Series, controls: pd.DataFrame) -> np.ndarray:
    ranked_y = pd.to_numeric(series, errors="coerce").rank(method="average").to_numpy(dtype=float)
    ranked_controls = controls.apply(pd.to_numeric, errors="coerce").rank(method="average")
    design = np.column_stack(
        [np.ones(len(ranked_controls), dtype=float), ranked_controls.to_numpy(dtype=float)]
    )
    beta, *_ = np.linalg.lstsq(design, ranked_y, rcond=None)
    return ranked_y - design @ beta


def partial_spearman(
    signal: pd.Series,
    target: pd.Series,
    controls: pd.DataFrame,
) -> tuple[int, float]:
    frame = pd.concat(
        [
            pd.to_numeric(signal, errors="coerce").rename("signal"),
            pd.to_numeric(target, errors="coerce").rename("target"),
            controls.apply(pd.to_numeric, errors="coerce"),
        ],
        axis=1,
    ).replace([np.inf, -np.inf], np.nan).dropna()
    n = len(frame)
    if n < max(5, controls.shape[1] + 3):
        return n, float("nan")

    control_columns = [column for column in frame.columns if column not in {"signal", "target"}]
    x_resid = _rank_residual(frame["signal"], frame[control_columns])
    y_resid = _rank_residual(frame["target"], frame[control_columns])
    if np.std(x_resid) <= 1e-12 or np.std(y_resid) <= 1e-12:
        return n, float("nan")
    return n, float(np.corrcoef(x_resid, y_resid)[0, 1])


def _spearman(signal: pd.Series, target: pd.Series) -> tuple[int, float]:
    frame = pd.DataFrame(
        {
            "signal": pd.to_numeric(signal, errors="coerce"),
            "target": pd.to_numeric(target, errors="coerce"),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    n = len(frame)
    if n < 3:
        return n, float("nan")
    return n, float(
        frame["signal"].rank(method="average").corr(
            frame["target"].rank(method="average"), method="pearson"
        )
    )


def score_incremental_hedge_information(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    min_volume_coverage: float = 0.90,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
) -> pd.DataFrame:
    """Measure hedge-flow information beyond momentum and the paired raw-flow signal.

    The sample is restricted to common causal timestamps with at least the
    requested classified-volume Greek coverage. For each fixed raw/hedge pair,
    this reports ordinary Spearman association plus rank-partial correlations:

    * hedge | contemporaneous move
    * hedge | contemporaneous move + paired raw flow

    ``backward_return_1m_bps`` is the completed flow-minute SPX move already
    known when the feature becomes available at M+1. Controlling for it helps
    distinguish reactive/momentum-linked flow from incremental forward content.
    This remains a descriptive one-day diagnostic, not a causal estimator.
    """
    sample = matched_with_coverage(
        raw,
        hedge,
        min_volume_coverage=min_volume_coverage,
    )
    momentum_column = "backward_return_1m_bps"
    if momentum_column not in sample.columns:
        raise ValueError(f"hedge frame must contain {momentum_column}")

    rows: list[dict[str, object]] = []
    for raw_horizon in horizons_minutes:
        horizon = int(raw_horizon)
        target_column = f"forward_return_{horizon}m_bps"
        if target_column not in sample.columns:
            continue
        target = sample[target_column]
        baseline_n, baseline_spearman = _spearman(sample[momentum_column], target)

        for pair_name, raw_signal, hedge_signal in CORE_SIGNAL_PAIRS:
            if raw_signal not in sample.columns or hedge_signal not in sample.columns:
                continue
            raw_n, raw_spearman = _spearman(sample[raw_signal], target)
            hedge_n, hedge_spearman = _spearman(sample[hedge_signal], target)
            partial_momentum_n, hedge_partial_momentum = partial_spearman(
                sample[hedge_signal],
                target,
                sample[[momentum_column]],
            )
            partial_both_n, hedge_partial_momentum_raw = partial_spearman(
                sample[hedge_signal],
                target,
                sample[[momentum_column, raw_signal]],
            )
            raw_partial_n, raw_partial_momentum = partial_spearman(
                sample[raw_signal],
                target,
                sample[[momentum_column]],
            )

            rows.append(
                {
                    "min_volume_coverage": float(min_volume_coverage),
                    "horizon_minutes": horizon,
                    "pair": pair_name,
                    "observations": min(raw_n, hedge_n, partial_momentum_n, partial_both_n, raw_partial_n),
                    "momentum_observations": baseline_n,
                    "momentum_spearman": baseline_spearman,
                    "raw_signal": raw_signal,
                    "raw_spearman": raw_spearman,
                    "raw_partial_spearman_controlling_momentum": raw_partial_momentum,
                    "hedge_signal": hedge_signal,
                    "hedge_spearman": hedge_spearman,
                    "hedge_partial_spearman_controlling_momentum": hedge_partial_momentum,
                    "hedge_partial_spearman_controlling_momentum_and_raw": hedge_partial_momentum_raw,
                    "mechanical_sign_consistent": bool(np.isfinite(hedge_spearman) and hedge_spearman > 0),
                }
            )

    return pd.DataFrame(rows)
