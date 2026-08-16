from __future__ import annotations

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_hedge_incremental import partial_spearman
from packages.gexy.tradeflow_hedge_robustness import matched_with_coverage
from packages.gexy.tradeflow_window_regime import assign_session_window


HEDGE = "hedge_delta_units"
RAW = "flow_net_signed_contracts"
MOMENTUM = "backward_return_1m_bps"
TARGET = "forward_return_15m_bps"
REQUIRED = (HEDGE, RAW, MOMENTUM, TARGET)


def _spearman(x: pd.Series, y: pd.Series) -> float:
    frame = pd.DataFrame({"x": pd.to_numeric(x, errors="coerce"), "y": pd.to_numeric(y, errors="coerce")})
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    if len(frame) < 3:
        return float("nan")
    return float(frame["x"].rank(method="average").corr(frame["y"].rank(method="average"), method="pearson"))


def frozen_opening_sample(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    min_volume_coverage: float = 0.90,
) -> pd.DataFrame:
    """Return the same complete-case opening 15m sample used by the Batch 4 validator."""
    sample = matched_with_coverage(raw, hedge, min_volume_coverage=min_volume_coverage)
    sample = assign_session_window(sample)
    sample = sample.loc[sample["session_window"] == "opening"].copy()
    missing = [column for column in REQUIRED if column not in sample.columns]
    if missing:
        raise ValueError("validation sample missing columns: " + ", ".join(missing))

    numeric = sample[list(REQUIRED)].apply(pd.to_numeric, errors="coerce")
    valid = ~numeric.replace([np.inf, -np.inf], np.nan).isna().any(axis=1)
    result = sample.loc[valid].copy().reset_index(drop=True)
    for column in REQUIRED:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    if len(result) < 5:
        raise ValueError("fewer than 5 complete frozen opening 15m observations")
    return result


def _rank_frame(sample: pd.DataFrame) -> pd.DataFrame:
    return sample[list(REQUIRED)].rank(method="average")


def _ols_residual(y: np.ndarray, x: np.ndarray) -> tuple[np.ndarray, float]:
    design = np.column_stack([np.ones(len(x), dtype=float), x])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    fitted = design @ beta
    residual = y - fitted
    ss_total = float(np.sum((y - np.mean(y)) ** 2))
    ss_resid = float(np.sum(residual**2))
    r2 = float("nan") if ss_total <= 1e-12 else 1.0 - ss_resid / ss_total
    return residual, r2


def _standardize(values: np.ndarray) -> np.ndarray:
    centered = values - np.mean(values)
    std = float(np.std(centered, ddof=0))
    if std <= 1e-12:
        return np.full(len(values), np.nan)
    return centered / std


def _loo_summary(sample: pd.DataFrame, *, controlled: bool, full_value: float) -> dict[str, object]:
    values: list[float] = []
    for index in range(len(sample)):
        subset = sample.drop(index=index).reset_index(drop=True)
        if controlled:
            _, value = partial_spearman(subset[HEDGE], subset[TARGET], subset[[MOMENTUM, RAW]])
        else:
            value = _spearman(subset[HEDGE], subset[TARGET])
        if np.isfinite(value):
            values.append(float(value))

    array = np.asarray(values, dtype=float)
    if len(array) == 0:
        return {
            "loo_count": 0,
            "loo_negative_count": 0,
            "loo_negative_pct": float("nan"),
            "loo_median": float("nan"),
            "loo_min": float("nan"),
            "loo_max": float("nan"),
            "loo_max_abs_change": float("nan"),
            "loo_any_sign_flip": False,
        }
    full_sign = np.sign(full_value) if np.isfinite(full_value) else 0.0
    signs = np.sign(array)
    sign_flip = bool(full_sign != 0 and np.any((signs != 0) & (signs != full_sign)))
    return {
        "loo_count": int(len(array)),
        "loo_negative_count": int(np.sum(array < 0)),
        "loo_negative_pct": float(np.mean(array < 0)),
        "loo_median": float(np.median(array)),
        "loo_min": float(np.min(array)),
        "loo_max": float(np.max(array)),
        "loo_max_abs_change": float(np.max(np.abs(array - full_value))),
        "loo_any_sign_flip": sign_flip,
    }


def _contribution_summary(sample: pd.DataFrame, *, controlled: bool) -> dict[str, object]:
    ranks = _rank_frame(sample)
    if controlled:
        controls = ranks[[MOMENTUM, RAW]].to_numpy(dtype=float)
        hedge_values, _ = _ols_residual(ranks[HEDGE].to_numpy(dtype=float), controls)
        target_values, _ = _ols_residual(ranks[TARGET].to_numpy(dtype=float), controls)
    else:
        hedge_values = ranks[HEDGE].to_numpy(dtype=float)
        target_values = ranks[TARGET].to_numpy(dtype=float)

    hedge_z = _standardize(hedge_values)
    target_z = _standardize(target_values)
    contributions = hedge_z * target_z
    abs_contributions = np.abs(contributions)
    total_abs = float(np.nansum(abs_contributions))
    order = np.argsort(-np.nan_to_num(abs_contributions, nan=-np.inf))

    def share(k: int) -> float:
        if total_abs <= 1e-12:
            return float("nan")
        return float(np.nansum(abs_contributions[order[:k]]) / total_abs)

    largest_index = int(order[0]) if len(order) else -1
    if largest_index >= 0:
        if "timestamp" in sample.columns:
            largest_timestamp = str(sample.iloc[largest_index]["timestamp"])
        elif "flow_minute" in sample.columns:
            largest_timestamp = str(sample.iloc[largest_index]["flow_minute"])
        else:
            largest_timestamp = str(largest_index)
        largest_sign = int(np.sign(contributions[largest_index])) if np.isfinite(contributions[largest_index]) else 0
    else:
        largest_timestamp = ""
        largest_sign = 0

    return {
        "largest_abs_contribution_share": share(1),
        "top3_abs_contribution_share": share(3),
        "top5_abs_contribution_share": share(5),
        "largest_abs_contribution_timestamp": largest_timestamp,
        "largest_abs_contribution_sign": largest_sign,
    }


def audit_day(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    trading_day: str,
    min_volume_coverage: float = 0.90,
) -> dict[str, object]:
    sample = frozen_opening_sample(raw, hedge, min_volume_coverage=min_volume_coverage)

    ordinary = _spearman(sample[HEDGE], sample[TARGET])
    _, partial_momentum = partial_spearman(sample[HEDGE], sample[TARGET], sample[[MOMENTUM]])
    _, partial_raw = partial_spearman(sample[HEDGE], sample[TARGET], sample[[RAW]])
    _, partial_both = partial_spearman(sample[HEDGE], sample[TARGET], sample[[MOMENTUM, RAW]])

    ranks = _rank_frame(sample)
    controls = ranks[[MOMENTUM, RAW]].to_numpy(dtype=float)
    hedge_resid, hedge_r2 = _ols_residual(ranks[HEDGE].to_numpy(dtype=float), controls)
    target_resid, target_r2 = _ols_residual(ranks[TARGET].to_numpy(dtype=float), controls)

    ordinary_loo = _loo_summary(sample, controlled=False, full_value=ordinary)
    controlled_loo = _loo_summary(sample, controlled=True, full_value=partial_both)
    ordinary_contrib = _contribution_summary(sample, controlled=False)
    controlled_contrib = _contribution_summary(sample, controlled=True)

    row: dict[str, object] = {
        "trading_day": str(trading_day),
        "observations": int(len(sample)),
        "ordinary_spearman": ordinary,
        "partial_controlling_momentum": float(partial_momentum),
        "partial_controlling_raw": float(partial_raw),
        "partial_controlling_both": float(partial_both),
        "hedge_raw_spearman": _spearman(sample[HEDGE], sample[RAW]),
        "hedge_momentum_spearman": _spearman(sample[HEDGE], sample[MOMENTUM]),
        "raw_momentum_spearman": _spearman(sample[RAW], sample[MOMENTUM]),
        "rank_hedge_r2_from_both_controls": float(hedge_r2),
        "rank_target_r2_from_both_controls": float(target_r2),
        "rank_hedge_residual_std": float(np.std(hedge_resid, ddof=0)),
        "rank_target_residual_std": float(np.std(target_resid, ddof=0)),
    }
    row.update({f"ordinary_{key}": value for key, value in ordinary_loo.items()})
    row.update({f"controlled_{key}": value for key, value in controlled_loo.items()})
    row.update({f"ordinary_{key}": value for key, value in ordinary_contrib.items()})
    row.update({f"controlled_{key}": value for key, value in controlled_contrib.items()})
    return row
