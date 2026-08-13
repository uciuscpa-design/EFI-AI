from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .feature_engine import build_feature_state
from .market_adapter import MarketSnapshot, OptionSnapshot

DATA_BASE = "https://data.alpaca.markets"
PAPER_BASE = "https://paper-api.alpaca.markets"


@dataclass(frozen=True)
class AlpacaProviderConfig:
    underlying: str = "SPX"
    feed: str = "indicative"
    strike_width: float = 250.0
    expiration_days: int = 14
    risk_free_rate: float = 0.0
    dealer_call_sign: float = -1.0
    dealer_put_sign: float = -1.0
    positioning_confidence: float = 0.5


@dataclass(frozen=True)
class ProviderObservation:
    timestamp: datetime
    spot: float
    feature_state: Any
    quote_times: tuple[datetime, ...]


class AlpacaHttpClient:
    """Minimal read-only Alpaca REST client using environment credentials."""

    def __init__(self, key_id: str | None = None, secret_key: str | None = None) -> None:
        self.key_id = key_id or os.getenv("APCA_API_KEY_ID")
        self.secret_key = secret_key or os.getenv("APCA_API_SECRET_KEY")
        if not self.key_id or not self.secret_key:
            raise RuntimeError("APCA_API_KEY_ID and APCA_API_SECRET_KEY are required")

    def get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if params:
            clean = {k: v for k, v in params.items() if v is not None}
            url = f"{url}?{urlencode(clean)}"
        request = Request(
            url,
            headers={
                "APCA-API-KEY-ID": self.key_id,
                "APCA-API-SECRET-KEY": self.secret_key,
                "Accept": "application/json",
            },
            method="GET",
        )
        with urlopen(request, timeout=15) as response:  # nosec B310 - fixed HTTPS Alpaca hosts
            return json.loads(response.read().decode("utf-8"))


def _norm_pdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)


def _norm_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _bs_price(option_type: str, s: float, k: float, t: float, r: float, sigma: float) -> float:
    if t <= 0 or sigma <= 0:
        intrinsic = max(0.0, s - k) if option_type == "call" else max(0.0, k - s)
        return intrinsic
    root_t = math.sqrt(t)
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * root_t)
    d2 = d1 - sigma * root_t
    disc = math.exp(-r * t)
    if option_type == "call":
        return s * _norm_cdf(d1) - k * disc * _norm_cdf(d2)
    return k * disc * _norm_cdf(-d2) - s * _norm_cdf(-d1)


def implied_volatility(option_type: str, price: float, s: float, k: float, t: float, r: float = 0.0) -> float | None:
    if price <= 0 or s <= 0 or k <= 0 or t <= 0:
        return None
    lo, hi = 1e-4, 5.0
    low_price = _bs_price(option_type, s, k, t, r, lo)
    high_price = _bs_price(option_type, s, k, t, r, hi)
    if price < low_price - 1e-9 or price > high_price + 1e-9:
        return None
    for _ in range(80):
        mid = (lo + hi) / 2.0
        value = _bs_price(option_type, s, k, t, r, mid)
        if value > price:
            hi = mid
        else:
            lo = mid
    return (lo + hi) / 2.0


def black_scholes_gamma(s: float, k: float, t: float, r: float, sigma: float) -> float:
    if s <= 0 or k <= 0 or t <= 0 or sigma <= 0:
        return 0.0
    root_t = math.sqrt(t)
    d1 = (math.log(s / k) + (r + 0.5 * sigma * sigma) * t) / (sigma * root_t)
    return _norm_pdf(d1) / (s * sigma * root_t)


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _expiry_datetime(expiration_date: str) -> datetime:
    day = datetime.fromisoformat(expiration_date).date()
    # Use the regular-session close as a stable European-option expiry proxy.
    return datetime.combine(day, time(20, 0), tzinfo=timezone.utc)


def _mid(snapshot: dict[str, Any]) -> float | None:
    quote = snapshot.get("latestQuote") or snapshot.get("latest_quote") or {}
    bid = quote.get("bp", quote.get("bid_price"))
    ask = quote.get("ap", quote.get("ask_price"))
    if bid is None or ask is None or bid < 0 or ask <= 0 or ask < bid:
        return None
    return (float(bid) + float(ask)) / 2.0


def infer_forward_spot(chain: dict[str, Any], contracts: dict[str, dict[str, Any]]) -> float:
    """Infer an SPX reference from same-strike call/put parity mids.

    With r ~= 0 over short horizons, C-P ~= S-K. The median across matched
    strikes is much more robust than substituting SPY*10 for SPX.
    """
    paired: dict[tuple[str, float], dict[str, float]] = {}
    for symbol, snap in chain.items():
        meta = contracts.get(symbol)
        if not meta:
            continue
        mid = _mid(snap)
        if mid is None:
            continue
        key = (meta["expiration_date"], float(meta["strike_price"]))
        paired.setdefault(key, {})[meta["type"]] = mid
    estimates = []
    for (_, strike), sides in paired.items():
        if "call" in sides and "put" in sides:
            estimates.append(strike + sides["call"] - sides["put"])
    if not estimates:
        raise RuntimeError("cannot infer SPX reference: no matched call/put quotes")
    estimates.sort()
    return estimates[len(estimates) // 2]


class AlpacaSpxSnapshotProvider:
    """Build one normalized GEXY SPX observation from Alpaca option data."""

    def __init__(self, client: AlpacaHttpClient | None = None, config: AlpacaProviderConfig | None = None) -> None:
        self.client = client or AlpacaHttpClient()
        self.config = config or AlpacaProviderConfig()

    def _contracts(self, observation_time: datetime) -> list[dict[str, Any]]:
        end = observation_time.date().toordinal() + self.config.expiration_days
        end_date = datetime.fromordinal(end).date().isoformat()
        payload = self.client.get(
            f"{PAPER_BASE}/v2/options/contracts",
            {
                "underlying_symbols": self.config.underlying,
                "status": "active",
                "expiration_date_gte": observation_time.date().isoformat(),
                "expiration_date_lte": end_date,
                "limit": 10000,
            },
        )
        return payload.get("option_contracts", [])

    def _chain(self) -> dict[str, Any]:
        payload = self.client.get(
            f"{DATA_BASE}/v1beta1/options/snapshots/{self.config.underlying}",
            {"feed": self.config.feed, "limit": 1000},
        )
        return payload.get("snapshots", payload.get("chain", {}))

    def __call__(self, scheduled_time: datetime) -> ProviderObservation:
        observation_time = datetime.now(timezone.utc)
        contracts = self._contracts(observation_time)
        by_symbol = {row["symbol"]: row for row in contracts}
        chain = self._chain()
        spot = infer_forward_spot(chain, by_symbol)

        lower = spot - self.config.strike_width
        upper = spot + self.config.strike_width
        grouped: dict[tuple[float, datetime], dict[str, float]] = {}
        quote_times: list[datetime] = []
        ivs: list[float] = []

        for symbol, snap in chain.items():
            meta = by_symbol.get(symbol)
            if not meta:
                continue
            strike = float(meta["strike_price"])
            if not lower <= strike <= upper:
                continue
            midpoint = _mid(snap)
            quote = snap.get("latestQuote") or snap.get("latest_quote") or {}
            qts = quote.get("t", quote.get("timestamp"))
            if midpoint is None or not qts:
                continue
            quote_times.append(_parse_ts(qts))
            expiry = _expiry_datetime(meta["expiration_date"])
            t = max((expiry - observation_time).total_seconds(), 0.0) / (365.0 * 24 * 3600)
            iv = implied_volatility(meta["type"], midpoint, spot, strike, t, self.config.risk_free_rate)
            if iv is None:
                continue
            gamma = black_scholes_gamma(spot, strike, t, self.config.risk_free_rate, iv)
            ivs.append(iv)
            oi = float(meta.get("open_interest") or 0.0)
            sign = self.config.dealer_call_sign if meta["type"] == "call" else self.config.dealer_put_sign
            # Convert raw gamma/OI into a signed gamma contribution; feature_engine
            # intentionally expects normalized signed contributions upstream.
            signed_gex = sign * self.config.positioning_confidence * gamma * oi * 100.0 * spot * spot * 0.01
            key = (strike, expiry)
            side = grouped.setdefault(key, {"call": 0.0, "put": 0.0, "call_oi": 0.0, "put_oi": 0.0})
            side[meta["type"]] += signed_gex
            side[f"{meta['type']}_oi"] += oi

        options = tuple(
            OptionSnapshot(
                symbol=f"{self.config.underlying}:{strike}:{expiry.date().isoformat()}",
                strike=strike,
                expiry=expiry,
                call_open_interest=values["call_oi"],
                put_open_interest=values["put_oi"],
                call_gamma=values["call"],
                put_gamma=values["put"],
                implied_volatility=(sum(ivs) / len(ivs)) if ivs else None,
            )
            for (strike, expiry), values in sorted(grouped.items())
        )
        if not options:
            raise RuntimeError("Alpaca returned no usable SPX option observations")
        market = MarketSnapshot(
            timestamp=observation_time,
            spot=spot,
            iv=(sum(ivs) / len(ivs)) if ivs else None,
            options=options,
        )
        state = build_feature_state(market)
        return ProviderObservation(observation_time, spot, state, tuple(quote_times))
