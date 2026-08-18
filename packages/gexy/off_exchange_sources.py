from __future__ import annotations

from collections.abc import Collection, Mapping
from dataclasses import dataclass

import numpy as np
import pandas as pd


MASSIVE_TRF_EXCHANGE_ID = 4

# Dataset-scoped Databento publisher IDs from the provider's current publisher
# metadata. They are intentionally scoped by dataset rather than treated as
# universal IDs. Callers may supply an override mapping if provider metadata
# changes.
DATABENTO_TRF_PUBLISHERS_BY_DATASET: dict[str, dict[int, str]] = {
    "XNAS.BASIC": {82: "FINN", 83: "FINC"},
    "EQUS.PLUS": {54: "FINN", 55: "FINY", 56: "FINC"},
    "EQUS.ALL": {68: "FINN", 69: "FINY", 70: "FINC"},
}


@dataclass(frozen=True)
class OffExchangeStreamContract:
    provider: str
    transport: str
    causal_timestamp: str
    off_exchange_rule: str
    notes: str


STREAM_CONTRACTS = {
    "massive": OffExchangeStreamContract(
        provider="massive",
        transport="websocket",
        causal_timestamp="SIP timestamp (t)",
        off_exchange_rule="exchange id 4 AND trf_id/trfi present",
        notes=(
            "Massive-specific rule only. Preserve participant and TRF timestamps when present; "
            "do not infer buyer/seller direction."
        ),
    ),
    "alpaca_sip": OffExchangeStreamContract(
        provider="alpaca_sip",
        transport="websocket",
        causal_timestamp="SIP trade timestamp (t)",
        off_exchange_rule="explicit exchange-code allow-list supplied by the source adapter",
        notes=(
            "Do not hard-code a generic code as universal. Resolve/verify Alpaca exchange metadata "
            "for the active SIP feed before activation."
        ),
    ),
    "databento": OffExchangeStreamContract(
        provider="databento",
        transport="native live stream",
        causal_timestamp="Databento capture receive timestamp (ts_recv)",
        off_exchange_rule="dataset-scoped FINRA/TRF publisher_id allow-list",
        notes=(
            "Use publisher_id to identify FINRA/Nasdaq or FINRA/NYSE TRF records. The trade side is "
            "not treated as aggressor direction on Nasdaq Basic/TRF data."
        ),
    ),
}


BASE_COLUMNS = (
    "available_at",
    "symbol",
    "price",
    "size",
    "notional",
    "reporting_venue",
    "source",
    "off_exchange_observed",
    "available_at_basis",
)


def _require_columns(frame: pd.DataFrame, required: Collection[str], *, label: str) -> None:
    missing = sorted(set(required).difference(frame.columns))
    if missing:
        raise ValueError(f"{label} frame missing required columns: {', '.join(missing)}")


def _unix_timestamp_to_utc(values: pd.Series) -> pd.Series:
    """Convert Unix timestamps with second/ms/us/ns magnitudes to UTC timestamps."""
    numeric = pd.to_numeric(values, errors="coerce")
    finite = numeric[np.isfinite(numeric)]
    if finite.empty:
        return pd.to_datetime(numeric, utc=True, errors="coerce")

    magnitude = float(finite.abs().median())
    if magnitude >= 1e17:
        unit = "ns"
    elif magnitude >= 1e14:
        unit = "us"
    elif magnitude >= 1e11:
        unit = "ms"
    else:
        unit = "s"
    return pd.to_datetime(numeric, unit=unit, utc=True, errors="coerce")


def _finalize(
    frame: pd.DataFrame,
    *,
    source: str,
    available_at_basis: str,
    metadata: Mapping[str, pd.Series | object] | None = None,
) -> pd.DataFrame:
    result = pd.DataFrame(
        {
            "available_at": pd.to_datetime(frame["_available_at"], utc=True, errors="coerce"),
            "symbol": frame["_symbol"].astype("string"),
            "price": pd.to_numeric(frame["_price"], errors="coerce"),
            "size": pd.to_numeric(frame["_size"], errors="coerce"),
            "reporting_venue": frame["_reporting_venue"].astype("string"),
        }
    )
    result = result.dropna(subset=["available_at", "symbol", "price", "size", "reporting_venue"])
    result = result.loc[(result["price"] > 0) & (result["size"] > 0)].copy()
    result["notional"] = result["price"] * result["size"]
    result["source"] = source
    result["off_exchange_observed"] = True
    result["available_at_basis"] = available_at_basis

    if metadata:
        for name, values in metadata.items():
            if isinstance(values, pd.Series):
                result[name] = values.reindex(result.index)
            else:
                result[name] = values

    ordered = list(BASE_COLUMNS) + [column for column in result.columns if column not in BASE_COLUMNS]
    return result[ordered].sort_values(["available_at", "symbol", "price"]).reset_index(drop=True)


def normalize_massive_stock_trades(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize Massive stock WebSocket trades that are explicitly TRF/off-exchange.

    Massive documents dark/off-exchange stock trades as exchange ID 4 with a
    TRF identifier present. This rule is vendor-specific and is deliberately
    contained in this adapter.

    ``available_at`` uses the SIP timestamp ``t``. When present, ``pt`` and
    ``trft`` are preserved separately as participant/execution and TRF-report
    timestamps; neither is allowed to make the event available earlier.
    """
    _require_columns(raw, {"ev", "sym", "x", "p", "s", "t", "trfi"}, label="Massive")
    frame = raw.copy()
    exchange_id = pd.to_numeric(frame["x"], errors="coerce")
    trf_id = pd.to_numeric(frame["trfi"], errors="coerce")
    is_trade = frame["ev"].astype("string").str.upper().eq("T")
    is_off_exchange = is_trade & exchange_id.eq(MASSIVE_TRF_EXCHANGE_ID) & trf_id.notna()
    frame = frame.loc[is_off_exchange].copy()
    if frame.empty:
        return pd.DataFrame(columns=list(BASE_COLUMNS))

    exchange_id = pd.to_numeric(frame["x"], errors="coerce")
    trf_id = pd.to_numeric(frame["trfi"], errors="coerce")
    frame["_available_at"] = _unix_timestamp_to_utc(frame["t"])
    frame["_symbol"] = frame["sym"]
    frame["_price"] = frame["p"]
    frame["_size"] = frame["s"]
    frame["_reporting_venue"] = "MASSIVE_TRF_" + trf_id.astype("Int64").astype("string")

    metadata: dict[str, pd.Series | object] = {
        "vendor_exchange_id": exchange_id.astype("Int64"),
        "trf_id": trf_id.astype("Int64"),
    }
    if "pt" in frame.columns:
        metadata["source_event_at"] = _unix_timestamp_to_utc(frame["pt"])
    if "trft" in frame.columns:
        metadata["trf_reported_at"] = _unix_timestamp_to_utc(frame["trft"])
    if "i" in frame.columns:
        metadata["vendor_trade_id"] = frame["i"]
    if "z" in frame.columns:
        metadata["tape"] = frame["z"]
    if "c" in frame.columns:
        metadata["trade_conditions"] = frame["c"]
    if "q" in frame.columns:
        metadata["sequence_number"] = frame["q"]

    return _finalize(
        frame,
        source="massive_stocks_sip",
        available_at_basis="sip_timestamp",
        metadata=metadata,
    )


def normalize_alpaca_sip_trades(
    raw: pd.DataFrame,
    *,
    off_exchange_codes: Collection[str],
) -> pd.DataFrame:
    """Normalize Alpaca SIP stock trades using an explicit exchange-code allow-list.

    The adapter intentionally has no default off-exchange code. Alpaca exposes a
    stock exchange-code metadata endpoint and the active mapping must be verified
    for the SIP feed before activation. This prevents a vendor code from becoming
    an undocumented universal market rule inside GEXY.
    """
    _require_columns(raw, {"T", "S", "x", "p", "s", "t"}, label="Alpaca SIP")
    allowed = {str(value).strip().upper() for value in off_exchange_codes if str(value).strip()}
    if not allowed:
        raise ValueError("Alpaca SIP off_exchange_codes must contain at least one explicit code")

    frame = raw.copy()
    code = frame["x"].astype("string").str.strip().str.upper()
    is_trade = frame["T"].astype("string").str.lower().eq("t")
    frame = frame.loc[is_trade & code.isin(allowed)].copy()
    if frame.empty:
        return pd.DataFrame(columns=list(BASE_COLUMNS))

    code = frame["x"].astype("string").str.strip().str.upper()
    frame["_available_at"] = pd.to_datetime(frame["t"], utc=True, errors="coerce")
    frame["_symbol"] = frame["S"]
    frame["_price"] = frame["p"]
    frame["_size"] = frame["s"]
    frame["_reporting_venue"] = "ALPACA_SIP_" + code

    metadata: dict[str, pd.Series | object] = {"vendor_exchange_code": code}
    if "i" in frame.columns:
        metadata["vendor_trade_id"] = frame["i"]
    if "z" in frame.columns:
        metadata["tape"] = frame["z"]
    if "c" in frame.columns:
        metadata["trade_conditions"] = frame["c"]

    return _finalize(
        frame,
        source="alpaca_sip",
        available_at_basis="sip_trade_timestamp",
        metadata=metadata,
    )


def normalize_databento_equity_trades(
    raw: pd.DataFrame,
    *,
    dataset: str,
    trf_publishers: Mapping[int, str] | None = None,
) -> pd.DataFrame:
    """Normalize Databento equity trades from explicit TRF publisher IDs.

    By default, the adapter uses a dataset-scoped mapping of currently documented
    TRF publisher IDs. Callers can provide ``trf_publishers`` from live metadata
    to override the defaults. ``available_at`` is ``ts_recv`` so GEXY never acts
    on the earlier source-event timestamp before Databento captured the record.
    """
    _require_columns(
        raw,
        {"ts_recv", "symbol", "publisher_id", "price", "size"},
        label="Databento equity",
    )
    dataset_key = dataset.strip().upper()
    if trf_publishers is None:
        try:
            publisher_map = DATABENTO_TRF_PUBLISHERS_BY_DATASET[dataset_key]
        except KeyError as exc:
            known = ", ".join(sorted(DATABENTO_TRF_PUBLISHERS_BY_DATASET))
            raise ValueError(
                f"no default Databento TRF publisher map for {dataset_key}; "
                f"supply trf_publishers explicitly (known defaults: {known})"
            ) from exc
    else:
        publisher_map = {int(key): str(value).strip().upper() for key, value in trf_publishers.items()}
        if not publisher_map:
            raise ValueError("trf_publishers must not be empty")

    frame = raw.copy()
    publisher_id = pd.to_numeric(frame["publisher_id"], errors="coerce").astype("Int64")
    venue = publisher_id.map(publisher_map)
    frame = frame.loc[venue.notna()].copy()
    if frame.empty:
        return pd.DataFrame(columns=list(BASE_COLUMNS))

    publisher_id = pd.to_numeric(frame["publisher_id"], errors="coerce").astype("Int64")
    venue = publisher_id.map(publisher_map)
    frame["_available_at"] = pd.to_datetime(frame["ts_recv"], utc=True, errors="coerce")
    frame["_symbol"] = frame["symbol"]
    frame["_price"] = frame["price"]
    frame["_size"] = frame["size"]
    frame["_reporting_venue"] = venue.astype("string")

    metadata: dict[str, pd.Series | object] = {
        "publisher_id": publisher_id,
        "dataset": dataset_key,
    }
    if "ts_event" in frame.columns:
        metadata["source_event_at"] = pd.to_datetime(frame["ts_event"], utc=True, errors="coerce")
    if "side" in frame.columns:
        metadata["vendor_side"] = frame["side"]

    return _finalize(
        frame,
        source=f"databento:{dataset_key}",
        available_at_basis="databento_ts_recv",
        metadata=metadata,
    )
