from __future__ import annotations

import numpy as np
import pandas as pd

from packages.gexy.tradeflow_control_structure import score_control_structure
from packages.gexy.tradeflow_window_regime import assign_session_window


PRIMARY_HORIZON = 15
SPEC_COLUMNS = (
    ("ordinary", "hedge_target_spearman"),
    ("momentum_only", "hedge_partial_controlling_momentum"),
    ("raw_only", "hedge_partial_controlling_raw"),
    ("momentum_and_raw", "hedge_partial_controlling_momentum_and_raw"),
)


def _opening_only(frame: pd.DataFrame) -> pd.DataFrame:
    labeled = assign_session_window(frame)
    return labeled.loc[labeled["session_window"] == "opening"].copy().reset_index(drop=True)


def evaluate_opening_control_day(
    raw: pd.DataFrame,
    hedge: pd.DataFrame,
    *,
    trading_day: str,
    min_volume_coverage: float = 0.90,
) -> pd.DataFrame:
    """Evaluate the frozen 15m control structure on opening-window rows only."""
    result = score_control_structure(
        _opening_only(raw),
        _opening_only(hedge),
        trading_day=trading_day,
        horizons_minutes=(PRIMARY_HORIZON,),
        min_volume_coverage=min_volume_coverage,
    )
    if result.empty:
        return result
    result.insert(1, "session_window", "opening")
    return result


def summarize_opening_control_days(per_day: pd.DataFrame) -> pd.DataFrame:
    """Summarize sign and median stability for the frozen control specifications."""
    if per_day.empty:
        return pd.DataFrame()

    row: dict[str, object] = {
        "horizon_minutes": PRIMARY_HORIZON,
        "days": int(per_day["trading_day"].nunique()),
    }
    for label, column in SPEC_COLUMNS:
        values = pd.to_numeric(per_day[column], errors="coerce").dropna()
        row[f"{label}_negative_days"] = int((values < 0).sum())
        row[f"{label}_negative_day_pct"] = float((values < 0).mean()) if len(values) else np.nan
        row[f"{label}_median"] = float(values.median()) if len(values) else np.nan

    flip_mask = per_day["ordinary_to_both_sign_flip"].fillna(False).astype(bool)
    flip_dates = per_day.loc[flip_mask, "trading_day"].astype(str).tolist()
    row["ordinary_to_both_sign_flip_days"] = int(flip_mask.sum())
    row["ordinary_to_both_sign_flip_dates"] = ",".join(flip_dates)
    return pd.DataFrame([row])
