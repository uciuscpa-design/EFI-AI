from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Iterable, Mapping

from .provider_normalizer import NormalizedOptionObservation, normalize_observation


@dataclass(frozen=True)
class HistoricalPage:
    observations: tuple[NormalizedOptionObservation, ...]
    next_page_token: str | None


class AlpacaHistoricalAdapter:
    """Thin provider boundary for Alpaca historical option bars.

    The HTTP client is injected so this module remains testable and does not
    embed credentials or a particular SDK. The fetcher must accept the query
    parameters described by Alpaca's options bars endpoint and return a mapping
    containing `bars` and optionally `next_page_token`.
    """

    def __init__(self, fetcher: Callable[[Mapping[str, Any]], Mapping[str, Any]]) -> None:
        self._fetcher = fetcher

    def pages(
        self,
        *,
        symbols: Iterable[str],
        start: datetime,
        end: datetime,
        timeframe: str = "1Min",
        feed: str = "indicative",
        limit: int = 10000,
    ) -> Iterable[HistoricalPage]:
        symbols_value = ",".join(symbols)
        if not symbols_value:
            raise ValueError("symbols cannot be empty")
        if start >= end:
            raise ValueError("start must be before end")
        if not 1 <= limit <= 10000:
            raise ValueError("limit must be between 1 and 10000")

        token: str | None = None
        while True:
            params: dict[str, Any] = {
                "symbols": symbols_value,
                "timeframe": timeframe,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "feed": feed,
                "limit": limit,
                "sort": "asc",
            }
            if token:
                params["page_token"] = token
            payload = self._fetcher(params)
            raw_bars = payload.get("bars", {})
            normalized: list[NormalizedOptionObservation] = []
            for symbol, bars in raw_bars.items():
                for bar in bars:
                    normalized.append(normalize_observation(symbol=symbol, **bar))
            token = payload.get("next_page_token")
            yield HistoricalPage(tuple(normalized), token)
            if not token:
                break
