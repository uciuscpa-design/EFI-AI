from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .alpaca_provider import (
    AlpacaSpxSnapshotProvider,
    _expiry_datetime,
    _mid,
    _parse_ts,
    black_scholes_gamma,
    implied_volatility,
    infer_forward_spot,
)
from .live_pipeline import LivePipelineResult, run_live_pipeline
from .market_adapter import MarketSnapshot, OptionSnapshot


@dataclass(frozen=True)
class AlpacaLiveResult:
    timestamp: datetime
    spot: float
    quote_times: tuple[datetime, ...]
    pipeline: LivePipelineResult


def build_alpaca_market_snapshot(
    provider: AlpacaSpxSnapshotProvider,
    *,
    observation_time: datetime | None = None,
) -> tuple[MarketSnapshot, tuple[datetime, ...]]:
    """Build the exact normalized MarketSnapshot needed by the live predictor.

    This adapter intentionally reuses the provider's acquisition and pricing
    primitives while preserving strike-level observations for the live pipeline.
    """
    now = observation_time or datetime.now(timezone.utc)
    contracts = provider._contracts(now)
    by_symbol = {row["symbol"]: row for row in contracts}
    chain = provider._chain()
    spot = infer_forward_spot(chain, by_symbol)

    lower = spot - provider.config.strike_width
    upper = spot + provider.config.strike_width
    grouped: dict[tuple[float, datetime], dict[str, Any]] = {}
    quote_times: list[datetime] = []
    all_ivs: list[float] = []

    for symbol, snap in chain.items():
        meta = by_symbol.get(symbol)
        if not meta:
            continue
        strike = float(meta["strike_price"])
        if not lower <= strike <= upper:
            continue
        midpoint = _mid(snap)
        quote = snap.get("latestQuote") or snap.get("latest_quote") or {}
        quote_ts = quote.get("t", quote.get("timestamp"))
        if midpoint is None or not quote_ts:
            continue
        quote_times.append(_parse_ts(quote_ts))
        expiry = _expiry_datetime(meta["expiration_date"])
        t = max((expiry - now).total_seconds(), 0.0) / (365.0 * 24 * 3600)
        iv = implied_volatility(meta["type"], midpoint, spot, strike, t, provider.config.risk_free_rate)
        if iv is None:
            continue
        gamma = black_scholes_gamma(spot, strike, t, provider.config.risk_free_rate, iv)
        all_ivs.append(iv)
        oi = float(meta.get("open_interest") or 0.0)
        sign = provider.config.dealer_call_sign if meta["type"] == "call" else provider.config.dealer_put_sign
        signed_gex = (
            sign
            * provider.config.positioning_confidence
            * gamma
            * oi
            * 100.0
            * spot
            * spot
            * 0.01
        )
        key = (strike, expiry)
        values = grouped.setdefault(
            key,
            {"call": 0.0, "put": 0.0, "call_oi": 0.0, "put_oi": 0.0, "ivs": []},
        )
        values[meta["type"]] += signed_gex
        values[f"{meta['type']}_oi"] += oi
        values["ivs"].append(iv)

    options = tuple(
        OptionSnapshot(
            symbol=f"{provider.config.underlying}:{strike}:{expiry.date().isoformat()}",
            strike=strike,
            expiry=expiry,
            call_open_interest=values["call_oi"],
            put_open_interest=values["put_oi"],
            call_gamma=values["call"],
            put_gamma=values["put"],
            implied_volatility=(sum(values["ivs"]) / len(values["ivs"])) if values["ivs"] else None,
        )
        for (strike, expiry), values in sorted(grouped.items())
    )
    if not options:
        raise RuntimeError("Alpaca returned no usable SPX option observations")

    snapshot = MarketSnapshot(
        timestamp=now,
        spot=spot,
        iv=(sum(all_ivs) / len(all_ivs)) if all_ivs else None,
        options=options,
    )
    return snapshot, tuple(quote_times)


def predict_from_alpaca(
    provider: AlpacaSpxSnapshotProvider | None = None,
    *,
    horizon_minutes: int = 30,
    observation_time: datetime | None = None,
) -> AlpacaLiveResult:
    source = provider or AlpacaSpxSnapshotProvider()
    snapshot, quote_times = build_alpaca_market_snapshot(source, observation_time=observation_time)
    pipeline = run_live_pipeline(snapshot, horizon_minutes=horizon_minutes)
    return AlpacaLiveResult(snapshot.timestamp, snapshot.spot, quote_times, pipeline)
