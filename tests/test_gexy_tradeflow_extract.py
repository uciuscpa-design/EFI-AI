from __future__ import annotations

from datetime import date, time
from pathlib import Path

import pandas as pd
import pytest

from scripts.gexy_tradeflow_extract import (
    _attach_chain_metadata,
    _classified_path,
    _classify_frame,
    _normalize_tcbbo,
    _raw_path,
    _summarize,
)


def test_raw_path_matches_downloader_filename(tmp_path: Path) -> None:
    path = _raw_path(tmp_path, date(2026, 8, 12), (time(9, 30), time(10, 0)))
    assert path.name == "gexy_spxw_2026-08-12_0930_1000_tcbbo.dbn.zst"


def test_classified_path_replaces_dbn_suffix() -> None:
    raw = Path("data/gexy/tradeflow/gexy_spxw_2026-08-12_0930_1000_tcbbo.dbn.zst")
    assert _classified_path(raw).name == "gexy_spxw_2026-08-12_0930_1000_tcbbo_classified.csv"


def test_normalize_tcbbo_restores_ts_recv_index_and_numeric_fields() -> None:
    raw = pd.DataFrame(
        {
            "symbol": [" SPXW  A "],
            "price": ["10.5"],
            "size": ["3"],
            "bid_px_00": ["10.0"],
            "ask_px_00": ["10.5"],
        },
        index=pd.DatetimeIndex(["2026-08-12T13:30:00Z"], name="ts_recv"),
    )

    normalized = _normalize_tcbbo(raw)

    assert normalized.loc[0, "symbol"] == "SPXW  A"
    assert normalized.loc[0, "price"] == pytest.approx(10.5)
    assert normalized.loc[0, "size"] == pytest.approx(3.0)
    assert str(normalized.loc[0, "ts_recv"].tz) == "UTC"


def test_classify_frame_uses_nbbo_and_keeps_vendor_side_only_as_untrusted() -> None:
    frame = pd.DataFrame(
        {
            "ts_recv": pd.to_datetime(
                [
                    "2026-08-12T13:30:00Z",
                    "2026-08-12T13:30:01Z",
                    "2026-08-12T13:30:02Z",
                ],
                utc=True,
            ),
            "symbol": ["a", "b", "c"],
            "price": [10.5, 10.0, 10.25],
            "size": [2.0, 3.0, 4.0],
            "bid_px_00": [10.0, 10.0, 10.0],
            "ask_px_00": [10.5, 10.5, 10.5],
            "side": ["A", "B", "N"],
        }
    )

    classified = _classify_frame(frame)

    assert classified["inferred_side"].tolist() == ["buy", "sell", "unknown"]
    assert classified["signed_side"].tolist() == [1, -1, 0]
    assert classified["signed_contracts"].tolist() == [2.0, -3.0, 0.0]
    assert classified["premium_notional"].tolist() == pytest.approx([2100.0, 3000.0, 4100.0])
    assert classified["signed_premium_notional"].tolist() == pytest.approx([2100.0, -3000.0, 0.0])
    assert "side" not in classified.columns
    assert classified["vendor_side_untrusted"].tolist() == ["A", "B", "N"]


def test_attach_chain_metadata_marks_matches() -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["SPXW  A", "SPXW  X"],
            "inferred_side": ["buy", "sell"],
            "signed_side": [1, -1],
            "size": [1.0, 2.0],
            "signed_contracts": [1.0, -2.0],
            "premium_notional": [100.0, 200.0],
            "signed_premium_notional": [100.0, -200.0],
        }
    )
    chain = pd.DataFrame(
        {
            "raw_symbol": ["SPXW  A"],
            "instrument_class": ["C"],
            "strike_price": [7760.0],
            "open_interest": [123.0],
        }
    )

    merged = _attach_chain_metadata(frame, chain)

    assert merged["chain_match"].tolist() == [True, False]
    assert merged.loc[0, "strike_price"] == pytest.approx(7760.0)
    assert pd.isna(merged.loc[1, "strike_price"])


def test_summary_reports_inferred_flow_without_vendor_labels(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {
            "symbol": ["a", "a", "b"],
            "inferred_side": ["buy", "sell", "unknown"],
            "size": [2.0, 3.0, 4.0],
            "signed_contracts": [2.0, -3.0, 0.0],
            "premium_notional": [200.0, 300.0, 400.0],
            "signed_premium_notional": [200.0, -300.0, 0.0],
            "chain_match": [True, True, False],
        }
    )

    summary = _summarize(frame, window_label="09:30-10:00", source=tmp_path / "pilot.dbn.zst")

    assert summary["records"] == 3
    assert summary["unique_symbols"] == 2
    assert summary["chain_matches"] == 2
    assert summary["buy_trades"] == 1
    assert summary["sell_trades"] == 1
    assert summary["unknown_trades"] == 1
    assert summary["unknown_trade_pct"] == pytest.approx(1 / 3)
    assert summary["contract_volume"] == pytest.approx(9.0)
    assert summary["net_signed_contracts"] == pytest.approx(-1.0)
    assert summary["net_signed_premium_notional"] == pytest.approx(-100.0)
