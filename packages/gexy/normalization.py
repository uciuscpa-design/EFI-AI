from __future__ import annotations

from datetime import date, datetime
from typing import Any

from packages.gexy.models import NormalizedOptionSurface, OptionSurfacePoint, OptionType


def _pick(mapping: dict[str, Any] | None, *keys: str) -> Any:
    if not mapping:
        return None
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _float(value: Any, default: float | None = None) -> float | None:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _datetime(value: Any) -> datetime | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value
    text = str(value).replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _snapshot_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    snapshots = payload.get("snapshots")
    if not isinstance(snapshots, dict):
        return {}
    return {
        str(symbol): snapshot
        for symbol, snapshot in snapshots.items()
        if isinstance(snapshot, dict)
    }


def normalize_alpaca_option_surface(
    contracts_payload: dict[str, Any],
    snapshots_payload: dict[str, Any],
) -> NormalizedOptionSurface:
    """Join Alpaca contract metadata/OI with snapshots using contract symbol."""
    raw_contracts = contracts_payload.get("option_contracts")
    if raw_contracts is None:
        raw_contracts = contracts_payload.get("contracts")
    if not isinstance(raw_contracts, list):
        raw_contracts = []

    snapshots = _snapshot_map(snapshots_payload)
    points: list[OptionSurfacePoint] = []
    invalid_contracts = 0
    missing_snapshots = 0

    for contract in raw_contracts:
        if not isinstance(contract, dict):
            invalid_contracts += 1
            continue

        symbol = str(contract.get("symbol") or "").strip().upper()
        underlying = str(contract.get("underlying_symbol") or "").strip().upper()
        expiration = _date(contract.get("expiration_date"))
        strike = _float(contract.get("strike_price"))
        multiplier = _float(contract.get("size"), 100.0)
        open_interest = _float(contract.get("open_interest"), 0.0)
        option_type_value = str(contract.get("type") or "").strip().lower()

        if (
            not symbol
            or not underlying
            or expiration is None
            or strike is None
            or strike <= 0
            or multiplier is None
            or multiplier <= 0
            or open_interest is None
            or open_interest < 0
            or option_type_value not in {"call", "put"}
        ):
            invalid_contracts += 1
            continue

        snapshot = snapshots.get(symbol)
        if snapshot is None:
            snapshot = {}
            missing_snapshots += 1

        quote = _pick(snapshot, "latest_quote", "latestQuote")
        if not isinstance(quote, dict):
            quote = {}
        trade = _pick(snapshot, "latest_trade", "latestTrade")
        if not isinstance(trade, dict):
            trade = {}
        greeks = snapshot.get("greeks")
        if not isinstance(greeks, dict):
            greeks = {}

        points.append(
            OptionSurfacePoint(
                symbol=symbol,
                underlying_symbol=underlying,
                expiration_date=expiration,
                option_type=OptionType(option_type_value),
                strike=strike,
                multiplier=multiplier,
                open_interest=open_interest,
                open_interest_date=_date(contract.get("open_interest_date")),
                bid=_float(_pick(quote, "bid_price", "bp")),
                ask=_float(_pick(quote, "ask_price", "ap")),
                bid_size=_float(_pick(quote, "bid_size", "bs")),
                ask_size=_float(_pick(quote, "ask_size", "as")),
                quote_timestamp=_datetime(_pick(quote, "timestamp", "t")),
                trade_price=_float(_pick(trade, "price", "p")),
                trade_size=_float(_pick(trade, "size", "s")),
                trade_timestamp=_datetime(_pick(trade, "timestamp", "t")),
                implied_volatility=_float(
                    _pick(snapshot, "implied_volatility", "impliedVolatility")
                ),
                delta=_float(greeks.get("delta")),
                gamma=_float(greeks.get("gamma")),
                theta=_float(greeks.get("theta")),
                vega=_float(greeks.get("vega")),
                rho=_float(greeks.get("rho")),
            )
        )

    points.sort(key=lambda point: (point.expiration_date, point.strike, point.option_type.value))
    return NormalizedOptionSurface(
        points=tuple(points),
        contracts_seen=len(raw_contracts),
        invalid_contracts=invalid_contracts,
        missing_snapshots=missing_snapshots,
    )
