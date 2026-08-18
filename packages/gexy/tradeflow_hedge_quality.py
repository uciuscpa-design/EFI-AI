from __future__ import annotations

import numpy as np
import pandas as pd


def aggregate_greek_volume_coverage(weighted_trades: pd.DataFrame) -> pd.DataFrame:
    """Measure how much classified contract volume has usable delta/gamma Greeks."""
    required = {"flow_minute", "size", "signed_side", "hedge_greek_available"}
    missing = sorted(required.difference(weighted_trades.columns))
    if missing:
        raise ValueError(f"weighted trade frame missing coverage columns: {', '.join(missing)}")

    frame = weighted_trades.copy()
    frame["flow_minute"] = pd.to_datetime(frame["flow_minute"], utc=True, errors="coerce")
    frame["size"] = pd.to_numeric(frame["size"], errors="coerce")
    frame["signed_side"] = pd.to_numeric(frame["signed_side"], errors="coerce")
    frame = frame.dropna(subset=["flow_minute", "size", "signed_side"]).copy()
    frame["classified"] = frame["signed_side"] != 0
    frame["solved"] = frame["classified"] & frame["hedge_greek_available"].fillna(False)

    rows: list[dict[str, object]] = []
    for minute, group in frame.groupby("flow_minute", sort=True):
        classified = group.loc[group["classified"]]
        solved = group.loc[group["solved"]]
        classified_volume = float(classified["size"].sum())
        solved_volume = float(solved["size"].sum())
        rows.append(
            {
                "flow_minute": pd.Timestamp(minute),
                "timestamp": pd.Timestamp(minute) + pd.to_timedelta(1, unit="min"),
                "hedge_greek_solved_contract_volume": solved_volume,
                "hedge_greek_solved_contract_volume_pct": (
                    solved_volume / classified_volume if classified_volume > 0 else np.nan
                ),
            }
        )

    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)
