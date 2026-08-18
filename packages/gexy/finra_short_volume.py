from __future__ import annotations

from collections.abc import Iterable
from io import StringIO
from pathlib import Path

import numpy as np
import pandas as pd


FINRA_DAILY_REQUIRED_COLUMNS = {
    "Date",
    "Symbol",
    "ShortVolume",
    "ShortExemptVolume",
    "TotalVolume",
    "Market",
}


def _safe_ratio(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    result = numerator.astype(float) / denominator.astype(float)
    return result.where(np.isfinite(result) & denominator.ne(0))


def read_finra_daily_short_volume(source: str | Path) -> pd.DataFrame:
    """Read a FINRA Daily Short Sale Volume pipe-delimited file.

    This function performs local parsing only. It does not download data or infer
    when a file became public.
    """
    path = Path(source)
    return pd.read_csv(path, sep="|", dtype="string")


def read_finra_daily_short_volume_text(text: str) -> pd.DataFrame:
    """Parse already-downloaded FINRA Daily Short Sale Volume text."""
    return pd.read_csv(StringIO(text), sep="|", dtype="string")


def normalize_finra_daily_short_volume(
    raw: pd.DataFrame,
    *,
    facility: str,
    available_at: str | pd.Timestamp,
) -> pd.DataFrame:
    """Normalize FINRA daily short-sale volume with explicit causal availability.

    ``available_at`` is required rather than inferred because FINRA states a
    latest publication deadline, while the exact time a given file became
    observable can vary. GEXY must use the time actually observed/recorded by the
    acquisition process.

    These fields describe short-sale *volume*, not short interest or net short
    positioning. The output intentionally contains no position or directional
    conviction field.
    """
    missing = sorted(FINRA_DAILY_REQUIRED_COLUMNS.difference(raw.columns))
    if missing:
        raise ValueError(f"FINRA daily short-volume frame missing columns: {', '.join(missing)}")

    observed_at = pd.Timestamp(available_at)
    if observed_at.tzinfo is None:
        raise ValueError("available_at must include an explicit timezone")
    observed_at = observed_at.tz_convert("UTC")

    frame = raw.copy()
    frame["trade_date"] = pd.to_datetime(
        frame["Date"].astype("string").str.strip(),
        format="%Y%m%d",
        errors="coerce",
    ).dt.date
    frame["symbol"] = frame["Symbol"].astype("string").str.strip().str.upper()
    frame["market"] = frame["Market"].astype("string").str.strip().str.upper()
    for source_column, target_column in (
        ("ShortVolume", "short_volume"),
        ("ShortExemptVolume", "short_exempt_volume"),
        ("TotalVolume", "total_volume"),
    ):
        frame[target_column] = pd.to_numeric(frame[source_column], errors="coerce")

    frame = frame.dropna(
        subset=["trade_date", "symbol", "short_volume", "short_exempt_volume", "total_volume"]
    ).copy()
    frame = frame.loc[frame["total_volume"] > 0].copy()
    frame["facility"] = facility.strip().upper()
    frame["available_at"] = observed_at
    frame["short_volume_ratio"] = _safe_ratio(frame["short_volume"], frame["total_volume"])
    frame["short_plus_exempt_ratio"] = _safe_ratio(
        frame["short_volume"] + frame["short_exempt_volume"],
        frame["total_volume"],
    )
    frame["context_type"] = "off_exchange_short_sale_volume"
    frame["is_position_measure"] = False

    columns = [
        "trade_date",
        "available_at",
        "symbol",
        "facility",
        "market",
        "short_volume",
        "short_exempt_volume",
        "total_volume",
        "short_volume_ratio",
        "short_plus_exempt_ratio",
        "context_type",
        "is_position_measure",
    ]
    return frame[columns].sort_values(["trade_date", "symbol", "facility"]).reset_index(drop=True)


def combine_finra_daily_short_volume(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    """Combine mutually exclusive facility-level normalized FINRA frames.

    Do not mix a consolidated FINRA file with its component TRF/ADF files or the
    same activity will be double-counted. Causal availability for the aggregate
    is the latest ``available_at`` among included component files.
    """
    pieces = [frame.copy() for frame in frames]
    if not pieces:
        raise ValueError("at least one FINRA normalized frame is required")

    combined = pd.concat(pieces, ignore_index=True, sort=False)
    required = {
        "trade_date",
        "available_at",
        "symbol",
        "facility",
        "short_volume",
        "short_exempt_volume",
        "total_volume",
    }
    missing = sorted(required.difference(combined.columns))
    if missing:
        raise ValueError(f"normalized FINRA frame missing columns: {', '.join(missing)}")

    combined["available_at"] = pd.to_datetime(combined["available_at"], utc=True, errors="coerce")
    rows: list[dict[str, object]] = []
    for (trade_date, symbol), group in combined.groupby(["trade_date", "symbol"], sort=True):
        short_volume = float(pd.to_numeric(group["short_volume"], errors="coerce").sum())
        short_exempt = float(pd.to_numeric(group["short_exempt_volume"], errors="coerce").sum())
        total_volume = float(pd.to_numeric(group["total_volume"], errors="coerce").sum())
        facilities = tuple(sorted(set(group["facility"].dropna().astype(str))))
        rows.append(
            {
                "trade_date": trade_date,
                "available_at": group["available_at"].max(),
                "symbol": symbol,
                "facility": "COMBINED_EXPLICIT",
                "source_facilities": ",".join(facilities),
                "source_facility_count": len(facilities),
                "short_volume": short_volume,
                "short_exempt_volume": short_exempt,
                "total_volume": total_volume,
                "short_volume_ratio": short_volume / total_volume if total_volume else np.nan,
                "short_plus_exempt_ratio": (
                    (short_volume + short_exempt) / total_volume if total_volume else np.nan
                ),
                "context_type": "off_exchange_short_sale_volume",
                "is_position_measure": False,
            }
        )
    return pd.DataFrame(rows).sort_values(["trade_date", "symbol"]).reset_index(drop=True)
