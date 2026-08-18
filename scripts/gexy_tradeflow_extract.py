from __future__ import annotations

import argparse
from datetime import date, time
from pathlib import Path

import pandas as pd

from packages.gexy.tradeflow import classify_trade_against_nbbo

try:
    from scripts.gexy_tradeflow_plan import (
        _chain_path,
        _filter_chain_by_strike_band,
        _opening_forward,
        _parse_windows,
        _window_label,
    )
except ModuleNotFoundError as exc:
    if exc.name != "scripts":
        raise
    from gexy_tradeflow_plan import (
        _chain_path,
        _filter_chain_by_strike_band,
        _opening_forward,
        _parse_windows,
        _window_label,
    )


DEFAULT_WINDOWS = _parse_windows("09:30-10:00,15:30-16:00")
DEFAULT_STRIKE_BAND_POINTS = 200.0
DEFAULT_DATA_DIR = Path("data/gexy/tradeflow")
SPX_MULTIPLIER = 100.0


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("--date must use YYYY-MM-DD") from exc


def _raw_path(data_dir: Path, day: date, window: tuple[time, time]) -> Path:
    start, end = window
    return data_dir / (
        f"gexy_spxw_{day.isoformat()}_{start.strftime('%H%M')}_{end.strftime('%H%M')}_tcbbo.dbn.zst"
    )


def _classified_path(raw_path: Path) -> Path:
    name = raw_path.name
    suffix = "_tcbbo.dbn.zst"
    if not name.endswith(suffix):
        return raw_path.with_suffix(raw_path.suffix + ".classified.csv")
    return raw_path.with_name(name[: -len(suffix)] + "_tcbbo_classified.csv")


def _summary_path(data_dir: Path, day: date) -> Path:
    return data_dir / f"gexy_spxw_{day.isoformat()}_tcbbo_summary.csv"


def _load_chain_metadata(day: date, band_points: float) -> tuple[float, pd.DataFrame]:
    if band_points <= 0:
        raise ValueError("strike band must be positive")

    path = _chain_path(day)
    if not path.exists():
        raise ValueError(f"cached chain was not found: {path}")

    chain = pd.read_csv(path)
    required = {"raw_symbol", "instrument_class", "strike_price", "open_interest"}
    missing = sorted(required.difference(chain.columns))
    if missing:
        raise ValueError(f"chain CSV missing required columns: {', '.join(missing)}")

    opening_forward = _opening_forward(day)
    selected = _filter_chain_by_strike_band(
        chain,
        anchor=opening_forward,
        band_points=band_points,
    ).copy()
    if selected.empty:
        raise ValueError(
            f"{day.isoformat()} strike band selected no contracts around opening forward {opening_forward:.3f}"
        )

    selected["raw_symbol"] = selected["raw_symbol"].astype(str).str.strip()
    selected["instrument_class"] = selected["instrument_class"].astype(str).str.upper()
    selected["strike_price"] = pd.to_numeric(selected["strike_price"], errors="coerce")
    selected["open_interest"] = pd.to_numeric(selected["open_interest"], errors="coerce")
    selected = selected.dropna(subset=["raw_symbol", "strike_price", "open_interest"])
    selected = selected[selected["instrument_class"].isin(["C", "P"])]
    selected = selected.drop_duplicates("raw_symbol", keep="last")
    return opening_forward, selected[
        ["raw_symbol", "instrument_class", "strike_price", "open_interest"]
    ].copy()


def _normalize_tcbbo(raw: pd.DataFrame) -> pd.DataFrame:
    frame = raw.copy()
    if "ts_recv" not in frame.columns:
        frame = frame.reset_index()

    required = {"ts_recv", "symbol", "price", "size", "bid_px_00", "ask_px_00"}
    missing = sorted(required.difference(frame.columns))
    if missing:
        raise ValueError(f"TCBBO data missing required columns: {', '.join(missing)}")

    frame["ts_recv"] = pd.to_datetime(frame["ts_recv"], utc=True, errors="coerce")
    if "ts_event" in frame.columns:
        frame["ts_event"] = pd.to_datetime(frame["ts_event"], utc=True, errors="coerce")

    for column in ("price", "size", "bid_px_00", "ask_px_00", "bid_sz_00", "ask_sz_00"):
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame["symbol"] = frame["symbol"].astype(str).str.strip()
    frame = frame.dropna(subset=["ts_recv", "symbol", "price", "size", "bid_px_00", "ask_px_00"])
    frame = frame[frame["size"] >= 0].copy()
    frame = frame.sort_values("ts_recv").reset_index(drop=True)
    return frame


def _classify_frame(frame: pd.DataFrame) -> pd.DataFrame:
    classified = frame.copy()
    results = [
        classify_trade_against_nbbo(
            float(row.price),
            float(row.bid_px_00),
            float(row.ask_px_00),
        )
        for row in classified[["price", "bid_px_00", "ask_px_00"]].itertuples(index=False)
    ]

    classified["inferred_side"] = [item.side.value for item in results]
    classified["signed_side"] = [item.signed_side for item in results]
    classified["classification_reason"] = [item.reason for item in results]
    classified["nbbo_midpoint"] = [item.midpoint for item in results]
    classified["nbbo_spread"] = [item.spread for item in results]
    classified["signed_contracts"] = classified["size"] * classified["signed_side"]
    classified["premium_notional"] = classified["price"] * classified["size"] * SPX_MULTIPLIER
    classified["signed_premium_notional"] = (
        classified["premium_notional"] * classified["signed_side"]
    )

    if "side" in classified.columns:
        classified = classified.rename(columns={"side": "vendor_side_untrusted"})

    return classified


def _attach_chain_metadata(frame: pd.DataFrame, chain: pd.DataFrame) -> pd.DataFrame:
    merged = frame.merge(
        chain,
        left_on="symbol",
        right_on="raw_symbol",
        how="left",
        validate="many_to_one",
    )
    merged["chain_match"] = merged["raw_symbol"].notna()
    return merged


def _summarize(frame: pd.DataFrame, *, window_label: str, source: Path) -> dict[str, object]:
    total = len(frame)
    buys = int((frame["inferred_side"] == "buy").sum())
    sells = int((frame["inferred_side"] == "sell").sum())
    unknown = int((frame["inferred_side"] == "unknown").sum())
    volume = float(frame["size"].sum())
    buy_volume = float(frame.loc[frame["inferred_side"] == "buy", "size"].sum())
    sell_volume = float(frame.loc[frame["inferred_side"] == "sell", "size"].sum())
    unknown_volume = float(frame.loc[frame["inferred_side"] == "unknown", "size"].sum())
    matched = int(frame["chain_match"].sum()) if "chain_match" in frame.columns else 0

    return {
        "window": window_label,
        "source": str(source),
        "records": total,
        "unique_symbols": int(frame["symbol"].nunique()),
        "chain_matches": matched,
        "chain_match_pct": matched / total if total else None,
        "buy_trades": buys,
        "sell_trades": sells,
        "unknown_trades": unknown,
        "unknown_trade_pct": unknown / total if total else None,
        "contract_volume": volume,
        "buy_contract_volume": buy_volume,
        "sell_contract_volume": sell_volume,
        "unknown_contract_volume": unknown_volume,
        "net_signed_contracts": float(frame["signed_contracts"].sum()),
        "gross_premium_notional": float(frame["premium_notional"].sum()),
        "net_signed_premium_notional": float(frame["signed_premium_notional"].sum()),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read previously purchased GEXY TCBBO DBN files, classify trade direction from the pre-trade NBBO, "
            "and write local classified CSVs plus a summary. This script makes no market-data requests."
        )
    )
    parser.add_argument("--date", required=True, type=_parse_date, dest="trading_day")
    parser.add_argument(
        "--windows",
        type=_parse_windows,
        default=DEFAULT_WINDOWS,
        help="comma-separated New York windows; default: 09:30-10:00,15:30-16:00",
    )
    parser.add_argument(
        "--strike-band-points",
        type=float,
        default=DEFAULT_STRIKE_BAND_POINTS,
        help="must match the downloader strike band; default: 200",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help="directory containing the purchased TCBBO DBN files",
    )
    args = parser.parse_args()

    try:
        opening_forward, chain = _load_chain_metadata(
            args.trading_day,
            float(args.strike_band_points),
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    try:
        import databento as db
    except ImportError as exc:
        raise SystemExit(
            "databento is not installed. Run with: uv run --with databento --with pandas python ..."
        ) from exc

    summaries: list[dict[str, object]] = []
    for window in args.windows:
        path = _raw_path(args.data_dir, args.trading_day, window)
        if not path.exists():
            raise SystemExit(f"purchased TCBBO file was not found: {path}")

        store = db.DBNStore.from_file(path)
        raw = store.to_df()
        try:
            normalized = _normalize_tcbbo(raw)
            classified = _classify_frame(normalized)
            classified = _attach_chain_metadata(classified, chain)
        except ValueError as exc:
            raise SystemExit(f"{path}: {exc}") from exc

        output = _classified_path(path)
        classified.to_csv(output, index=False)
        summary = _summarize(
            classified,
            window_label=_window_label(window),
            source=path,
        )
        summaries.append(summary)

        print(
            f"CLASSIFIED {_window_label(window)}: records={summary['records']} "
            f"symbols={summary['unique_symbols']} buys={summary['buy_trades']} "
            f"sells={summary['sell_trades']} unknown={summary['unknown_trades']} -> {output}"
        )

    summary_frame = pd.DataFrame(summaries)
    summary_path = _summary_path(args.data_dir, args.trading_day)
    summary_frame.to_csv(summary_path, index=False)

    print("\nGEXY TCBBO PILOT SUMMARY")
    print(summary_frame.to_string(index=False))
    print(f"OPENING FORWARD: {opening_forward:.6f}")
    print(f"SUMMARY CSV: {summary_path}")
    print(
        "NO PAID DATA REQUESTS: this extractor only reads the local DBN files already downloaded. "
        "Trade direction is inferred solely from trade price versus the pre-trade NBBO."
    )


if __name__ == "__main__":
    main()
