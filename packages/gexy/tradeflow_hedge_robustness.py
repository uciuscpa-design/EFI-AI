from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_diagnostics import align_raw_and_hedge_frames


CORE_SIGNAL_PAIRS = (
    ("net_contracts_vs_delta", "flow_net_signed_contracts", "hedge_delta_units"),
    ("call_contracts_vs_call_delta", "flow_signed_call_contracts", "hedge_call_delta_units"),
    ("put_contracts_vs_put_delta", "flow_signed_put_contracts", "hedge_put_delta_units"),
)

HEDGE_MECHANISM_SIGNALS = (
    "hedge_delta_units",
    "hedge_call_delta_units",
    "hedge_put_delta_units",
    "hedge_gamma_units_per_point",
    "hedge_call_gamma_units_per_point",
    "hedge_put_gamma_units_per_point",
)

DEFAULT_COVERAGE_FLOORS = (0.0, 0.80, 0.90, 0.95)


def _spearman(x: pd.Series, y: pd.Series) -> float:
    return float(x.rank(method="average").corr(y.rank(method="average"), method="pearson"))


def _directional_accuracy(x: np.ndarray, y: np.ndarray) -> float | None:
    mask = np.isfinite(x) & np.isfinite(y) & (x != 0) & (y != 0)
    if not mask.any():
        return None
    return float(np.mean(np.sign(x[mask]) == np.sign(y[mask])))


def _score(signal: pd.Series, target: pd.Series) -> dict[str, object]:
    data = pd.DataFrame(
        {
            "signal": pd.to_numeric(signal, errors="coerce"),
            "target": pd.to_numeric(target, errors="coerce"),
        }
    ).replace([np.inf, -np.inf], np.nan).dropna()
    n = len(data)
    if n < 3:
        pearson = float("nan")
        spearman = float("nan")
    else:
        pearson = float(data["signal"].corr(data["target"], method="pearson"))
        spearman = _spearman(data["signal"], data["target"])

    low_mean = high_mean = None
    low_n = high_n = 0
    if n >= 8 and data["signal"].nunique() >= 4:
        low_cut = float(data["signal"].quantile(0.25))
        high_cut = float(data["signal"].quantile(0.75))
        low = data.loc[data["signal"] <= low_cut, "target"]
        high = data.loc[data["signal"] >= high_cut, "target"]
        low_mean = float(low.mean()) if len(low) else None
        high_mean = float(high.mean()) if len(high) else None
        low_n = len(low)
        high_n = len(high)

    return {
        "observations": n,
        "spearman": spearman,
        "abs_spearman": abs(spearman) if np.isfinite(spearman) else float("nan"),
        "pearson": pearson,
        "directional_accuracy_same_sign": _directional_accuracy(
            data["signal"].to_numpy(dtype=float), data["target"].to_numpy(dtype=float)
        ),
        "bottom_quartile_mean_target_bps": low_mean,
        "top_quartile_mean_target_bps": high_mean,
        "top_minus_bottom_target_bps": (
            high_mean - low_mean if high_mean is not None and low_mean is not None else None
        ),
        "bottom_quartile_rows": low_n,
        "top_quartile_rows": high_n,
    }


def matched_with_coverage(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    min_volume_coverage: float = 0.0,
) -> pd.DataFrame:
    """Return common replay-matched timestamps above a classified-volume Greek floor."""
    if not 0.0 <= min_volume_coverage <= 1.0:
        raise ValueError("min_volume_coverage must be between 0 and 1")
    aligned = align_raw_and_hedge_frames(raw, hedge)
    if "replay_match" in aligned.columns:
        aligned = aligned.loc[aligned["replay_match"].fillna(False)].copy()
    coverage_column = "hedge_greek_solved_contract_volume_pct"
    if coverage_column not in aligned.columns:
        raise ValueError(f"hedge frame must contain {coverage_column}")
    coverage = pd.to_numeric(aligned[coverage_column], errors="coerce")
    return aligned.loc[coverage >= float(min_volume_coverage)].copy().reset_index(drop=True)


def lowest_coverage_rows(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    limit: int = 8,
) -> pd.DataFrame:
    """Return lowest Greek-volume-coverage replay-matched common timestamps."""
    aligned = matched_with_coverage(raw, hedge, min_volume_coverage=0.0)
    coverage = pd.to_numeric(
        aligned["hedge_greek_solved_contract_volume_pct"], errors="coerce"
    )
    result = aligned.assign(_coverage=coverage).dropna(subset=["_coverage"])
    columns = [
        "timestamp",
        "flow_minute",
        "hedge_greek_solved_pct",
        "hedge_greek_solved_contract_volume_pct",
        "hedge_classified_contract_volume",
        "hedge_greek_solved_contract_volume",
    ]
    available = [column for column in columns if column in result.columns]
    return result.sort_values("_coverage", ascending=True).head(limit)[available].reset_index(drop=True)


def score_core_pair_sensitivity(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
    coverage_floors: Iterable[float] = DEFAULT_COVERAGE_FLOORS,
) -> pd.DataFrame:
    """Score fixed raw-vs-hedge pairs across Greek-volume coverage floors.

    Pair identities are fixed before looking at results, avoiding best-of-eight
    signal selection within a family.
    """
    rows: list[dict[str, object]] = []
    for floor in coverage_floors:
        sample = matched_with_coverage(raw, hedge, min_volume_coverage=float(floor))
        for horizon in horizons_minutes:
            target_column = f"forward_return_{int(horizon)}m_bps"
            if target_column not in sample.columns:
                continue
            target = sample[target_column]
            for pair_name, raw_signal, hedge_signal in CORE_SIGNAL_PAIRS:
                for family, signal in (("raw_flow", raw_signal), ("hedge_flow", hedge_signal)):
                    if signal not in sample.columns:
                        continue
                    scored = _score(sample[signal], target)
                    rows.append(
                        {
                            "min_volume_coverage": float(floor),
                            "horizon_minutes": int(horizon),
                            "pair": pair_name,
                            "family": family,
                            "signal": signal,
                            **scored,
                        }
                    )
    return pd.DataFrame(rows)


def score_hedge_lead_lag(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    min_volume_coverage: float = 0.90,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
) -> pd.DataFrame:
    """Compare hedge signals with the flow-minute move and later forward returns.

    ``backward_return_1m_bps`` at availability timestamp M+1 is the replay move
    from M to M+1, i.e. contemporaneous with the trades aggregated from minute M.
    Forward targets begin only after the feature becomes available at M+1.
    """
    sample = matched_with_coverage(raw, hedge, min_volume_coverage=min_volume_coverage)
    targets: list[tuple[str, str]] = []
    if "backward_return_1m_bps" in sample.columns:
        targets.append(("contemporaneous_flow_minute", "backward_return_1m_bps"))
    for horizon in horizons_minutes:
        column = f"forward_return_{int(horizon)}m_bps"
        if column in sample.columns:
            targets.append((f"forward_{int(horizon)}m", column))
    if not targets:
        raise ValueError("hedge frame contains no contemporaneous or forward-return targets")

    rows: list[dict[str, object]] = []
    for signal in HEDGE_MECHANISM_SIGNALS:
        if signal not in sample.columns:
            continue
        for period, target_column in targets:
            scored = _score(sample[signal], sample[target_column])
            rows.append(
                {
                    "min_volume_coverage": float(min_volume_coverage),
                    "signal": signal,
                    "period": period,
                    "target": target_column,
                    **scored,
                }
            )
    return pd.DataFrame(rows)
