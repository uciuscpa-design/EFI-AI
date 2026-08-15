from __future__ import annotations

from collections.abc import Iterable

import numpy as np
import pandas as pd

from packages.gexy.replay import add_forward_horizon_labels


FLOW_FEATURES = (
    "flow_trade_records",
    "flow_unique_symbols",
    "flow_classification_rate",
    "flow_contract_volume",
    "flow_classified_contract_volume",
    "flow_unknown_contract_volume",
    "flow_net_signed_contracts",
    "flow_contract_imbalance",
    "flow_gross_premium_notional",
    "flow_classified_premium_notional",
    "flow_unknown_premium_notional",
    "flow_net_signed_premium_notional",
    "flow_premium_imbalance",
    "flow_buy_contract_volume",
    "flow_sell_contract_volume",
    "flow_signed_call_contracts",
    "flow_signed_put_contracts",
    "flow_signed_call_premium_notional",
    "flow_signed_put_premium_notional",
)


def _safe_ratio(numerator: float, denominator: float) -> float:
    if not np.isfinite(denominator) or denominator == 0:
        return float("nan")
    return float(numerator / denominator)


def aggregate_completed_minute_flow(classified: pd.DataFrame) -> pd.DataFrame:
    """Aggregate classified TCBBO trades into strictly causal completed-minute features.

    Every trade received during minute M is assigned an availability timestamp of
    M + 1 minute. This means a prediction stamped 09:31 may use all trades from
    09:30:00 through 09:30:59, but never any trade from the still-forming 09:31
    minute.
    """
    required = {
        "ts_recv",
        "symbol",
        "size",
        "instrument_class",
        "signed_side",
        "signed_contracts",
        "premium_notional",
        "signed_premium_notional",
    }
    missing = sorted(required.difference(classified.columns))
    if missing:
        raise ValueError(f"classified TCBBO frame missing required columns: {', '.join(missing)}")

    frame = classified.copy()
    frame["ts_recv"] = pd.to_datetime(frame["ts_recv"], utc=True, errors="coerce")
    for column in (
        "size",
        "signed_side",
        "signed_contracts",
        "premium_notional",
        "signed_premium_notional",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame["instrument_class"] = frame["instrument_class"].astype(str).str.upper()
    frame = frame.dropna(
        subset=[
            "ts_recv",
            "symbol",
            "size",
            "signed_side",
            "signed_contracts",
            "premium_notional",
            "signed_premium_notional",
        ]
    ).copy()
    if frame.empty:
        raise ValueError("classified TCBBO frame contains no usable trades")

    frame["flow_minute"] = frame["ts_recv"].dt.floor("min")
    frame["is_classified"] = frame["signed_side"] != 0
    frame["is_unknown"] = ~frame["is_classified"]
    frame["is_buy"] = frame["signed_side"] > 0
    frame["is_sell"] = frame["signed_side"] < 0
    frame["is_call"] = frame["instrument_class"] == "C"
    frame["is_put"] = frame["instrument_class"] == "P"

    rows: list[dict[str, object]] = []
    for minute, group in frame.groupby("flow_minute", sort=True):
        classified_group = group.loc[group["is_classified"]]
        unknown_group = group.loc[group["is_unknown"]]
        buy_group = group.loc[group["is_buy"]]
        sell_group = group.loc[group["is_sell"]]
        call_group = group.loc[group["is_call"]]
        put_group = group.loc[group["is_put"]]

        trade_records = len(group)
        classified_records = len(classified_group)
        contract_volume = float(group["size"].sum())
        classified_contract_volume = float(classified_group["size"].sum())
        unknown_contract_volume = float(unknown_group["size"].sum())
        net_signed_contracts = float(group["signed_contracts"].sum())
        gross_premium = float(group["premium_notional"].sum())
        classified_premium = float(classified_group["premium_notional"].sum())
        unknown_premium = float(unknown_group["premium_notional"].sum())
        net_signed_premium = float(group["signed_premium_notional"].sum())

        minute_timestamp = pd.Timestamp(minute).as_unit("ns")
        rows.append(
            {
                "flow_minute": minute_timestamp,
                "timestamp": minute_timestamp + pd.Timedelta(1, unit="min"),
                "flow_trade_records": trade_records,
                "flow_unique_symbols": int(group["symbol"].nunique()),
                "flow_classified_trade_records": classified_records,
                "flow_unknown_trade_records": len(unknown_group),
                "flow_classification_rate": _safe_ratio(classified_records, trade_records),
                "flow_contract_volume": contract_volume,
                "flow_classified_contract_volume": classified_contract_volume,
                "flow_unknown_contract_volume": unknown_contract_volume,
                "flow_net_signed_contracts": net_signed_contracts,
                "flow_contract_imbalance": _safe_ratio(
                    net_signed_contracts,
                    classified_contract_volume,
                ),
                "flow_gross_premium_notional": gross_premium,
                "flow_classified_premium_notional": classified_premium,
                "flow_unknown_premium_notional": unknown_premium,
                "flow_net_signed_premium_notional": net_signed_premium,
                "flow_premium_imbalance": _safe_ratio(
                    net_signed_premium,
                    classified_premium,
                ),
                "flow_buy_contract_volume": float(buy_group["size"].sum()),
                "flow_sell_contract_volume": float(sell_group["size"].sum()),
                "flow_signed_call_contracts": float(call_group["signed_contracts"].sum()),
                "flow_signed_put_contracts": float(put_group["signed_contracts"].sum()),
                "flow_signed_call_premium_notional": float(
                    call_group["signed_premium_notional"].sum()
                ),
                "flow_signed_put_premium_notional": float(
                    put_group["signed_premium_notional"].sum()
                ),
            }
        )

    return pd.DataFrame(rows).sort_values("timestamp").reset_index(drop=True)


def join_flow_to_replay(
    flow: pd.DataFrame,
    replay: pd.DataFrame,
    *,
    horizons_minutes: Iterable[int] = (1, 5, 15, 30, 60),
) -> pd.DataFrame:
    """Join completed-minute flow to same-timestamp replay state and future labels."""
    if "timestamp" not in flow.columns:
        raise ValueError("flow frame must contain timestamp")
    if "timestamp" not in replay.columns or "forward" not in replay.columns:
        raise ValueError("replay frame must contain timestamp and forward")

    left = flow.copy()
    left["timestamp"] = pd.to_datetime(left["timestamp"], utc=True, errors="coerce")
    left = left.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)

    right = replay.copy()
    right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True, errors="coerce")
    right = right.dropna(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    right = add_forward_horizon_labels(right, horizons_minutes)

    merged = left.merge(right, on="timestamp", how="left", validate="one_to_one", indicator=True)
    merged["replay_match"] = merged["_merge"] == "both"
    merged = merged.drop(columns=["_merge"])
    return merged.sort_values("timestamp").reset_index(drop=True)
