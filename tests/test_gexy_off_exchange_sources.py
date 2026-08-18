from __future__ import annotations

import pandas as pd
import pytest

from packages.gexy.finra_short_volume import (
    combine_finra_daily_short_volume,
    normalize_finra_daily_short_volume,
    read_finra_daily_short_volume_text,
)
from packages.gexy.institutional_13f import parse_13f_information_table_xml
from packages.gexy.off_exchange_sources import (
    normalize_alpaca_sip_trades,
    normalize_databento_equity_trades,
    normalize_massive_stock_trades,
)


def test_massive_requires_exchange_4_and_trf_identifier() -> None:
    raw = pd.DataFrame(
        {
            "ev": ["T", "T", "T"],
            "sym": ["SPY", "SPY", "AAPL"],
            "x": [4, 4, 11],
            "p": [650.0, 650.1, 230.0],
            "s": [1000, 200, 50],
            "t": [1_776_000_000_000, 1_776_000_000_100, 1_776_000_000_200],
            "pt": [1_776_000_000_000, 1_776_000_000_090, 1_776_000_000_190],
            "trfi": [201, None, None],
            "trft": [1_776_000_000_050, None, None],
            "i": ["a", "b", "c"],
            "z": [3, 3, 3],
        }
    )
    normalized = normalize_massive_stock_trades(raw)

    assert len(normalized) == 1
    assert normalized.loc[0, "symbol"] == "SPY"
    assert normalized.loc[0, "reporting_venue"] == "MASSIVE_TRF_201"
    assert normalized.loc[0, "available_at_basis"] == "sip_timestamp"
    assert normalized.loc[0, "trf_id"] == 201
    assert "signed_side" not in normalized.columns


def test_alpaca_sip_requires_explicit_off_exchange_code_allow_list() -> None:
    raw = pd.DataFrame(
        {
            "T": ["t", "t"],
            "S": ["SPY", "AAPL"],
            "x": ["D", "V"],
            "p": [650.0, 230.0],
            "s": [500, 100],
            "t": ["2026-08-17T13:30:01Z", "2026-08-17T13:30:02Z"],
            "i": [1, 2],
            "z": ["A", "C"],
        }
    )
    with pytest.raises(ValueError, match="off_exchange_codes"):
        normalize_alpaca_sip_trades(raw, off_exchange_codes=set())

    normalized = normalize_alpaca_sip_trades(raw, off_exchange_codes={"D"})
    assert len(normalized) == 1
    assert normalized.loc[0, "symbol"] == "SPY"
    assert normalized.loc[0, "reporting_venue"] == "ALPACA_SIP_D"
    assert normalized.loc[0, "available_at"] == pd.Timestamp("2026-08-17T13:30:01Z")


def test_databento_uses_dataset_scoped_trf_publishers_and_ts_recv() -> None:
    raw = pd.DataFrame(
        {
            "ts_recv": ["2026-08-17T13:30:01.100Z", "2026-08-17T13:30:01.200Z"],
            "ts_event": ["2026-08-17T13:30:01.090Z", "2026-08-17T13:30:01.190Z"],
            "symbol": ["SPY", "SPY"],
            "publisher_id": [82, 81],
            "price": [650.0, 650.01],
            "size": [700, 100],
            "side": ["N", "N"],
        }
    )
    normalized = normalize_databento_equity_trades(raw, dataset="XNAS.BASIC")

    assert len(normalized) == 1
    assert normalized.loc[0, "publisher_id"] == 82
    assert normalized.loc[0, "reporting_venue"] == "FINN"
    assert normalized.loc[0, "available_at"] == pd.Timestamp("2026-08-17T13:30:01.100Z")
    assert normalized.loc[0, "source_event_at"] == pd.Timestamp("2026-08-17T13:30:01.090Z")
    assert normalized.loc[0, "available_at"] > normalized.loc[0, "source_event_at"]


def test_databento_unknown_dataset_fails_closed_without_explicit_map() -> None:
    raw = pd.DataFrame(
        {
            "ts_recv": ["2026-08-17T13:30:01Z"],
            "symbol": ["SPY"],
            "publisher_id": [999],
            "price": [650.0],
            "size": [100],
        }
    )
    with pytest.raises(ValueError, match="supply trf_publishers explicitly"):
        normalize_databento_equity_trades(raw, dataset="FUTURE.DATASET")


def _finra_text(short_volume: int, total_volume: int) -> str:
    return (
        "Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market\n"
        f"20260817|SPY|{short_volume}|10|{total_volume}|Q\n"
    )


def test_finra_short_volume_is_causal_context_not_position() -> None:
    raw = read_finra_daily_short_volume_text(_finra_text(400, 1000))
    normalized = normalize_finra_daily_short_volume(
        raw,
        facility="FINRA_NASDAQ_TRF_CARTERET",
        available_at="2026-08-17T22:00:00-04:00",
    )

    assert normalized.loc[0, "short_volume_ratio"] == pytest.approx(0.4)
    assert normalized.loc[0, "available_at"] == pd.Timestamp("2026-08-18T02:00:00Z")
    assert not bool(normalized.loc[0, "is_position_measure"])
    assert "net_short_position" not in normalized.columns


def test_finra_available_at_must_be_timezone_aware() -> None:
    raw = read_finra_daily_short_volume_text(_finra_text(400, 1000))
    with pytest.raises(ValueError, match="explicit timezone"):
        normalize_finra_daily_short_volume(
            raw,
            facility="FINRA_NASDAQ_TRF_CARTERET",
            available_at="2026-08-17T18:00:00",
        )


def test_finra_facility_combination_uses_latest_component_availability() -> None:
    first = normalize_finra_daily_short_volume(
        read_finra_daily_short_volume_text(_finra_text(400, 1000)),
        facility="FINN",
        available_at="2026-08-17T17:50:00-04:00",
    )
    second = normalize_finra_daily_short_volume(
        read_finra_daily_short_volume_text(_finra_text(100, 500)),
        facility="FINY",
        available_at="2026-08-17T18:03:00-04:00",
    )
    combined = combine_finra_daily_short_volume([first, second])

    assert combined.loc[0, "short_volume"] == pytest.approx(500.0)
    assert combined.loc[0, "total_volume"] == pytest.approx(1500.0)
    assert combined.loc[0, "available_at"] == pd.Timestamp("2026-08-17T22:03:00Z")
    assert combined.loc[0, "source_facility_count"] == 2


def test_13f_parser_uses_filing_time_not_quarter_end_as_availability() -> None:
    xml = """<?xml version="1.0" encoding="UTF-8"?>
    <informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
      <infoTable>
        <nameOfIssuer>EXAMPLE CORP</nameOfIssuer>
        <titleOfClass>COM</titleOfClass>
        <cusip>123456789</cusip>
        <figi>BBG000000001</figi>
        <value>1500000</value>
        <shrsOrPrnAmt>
          <sshPrnamt>10000</sshPrnamt>
          <sshPrnamtType>SH</sshPrnamtType>
        </shrsOrPrnAmt>
        <investmentDiscretion>SOLE</investmentDiscretion>
        <votingAuthority>
          <Sole>10000</Sole>
          <Shared>0</Shared>
          <None>0</None>
        </votingAuthority>
      </infoTable>
    </informationTable>
    """
    holdings = parse_13f_information_table_xml(
        xml,
        manager="Example Manager",
        report_period="2026-06-30",
        filed_at="2026-08-14T16:05:00-04:00",
        accession="0000000000-26-000001",
        value_scale=1.0,
    )

    assert len(holdings) == 1
    assert holdings.loc[0, "report_period"].isoformat() == "2026-06-30"
    assert holdings.loc[0, "available_at"] == pd.Timestamp("2026-08-14T20:05:00Z")
    assert holdings.loc[0, "market_value_usd"] == pytest.approx(1_500_000.0)
    assert holdings.loc[0, "timing_precision"] == "quarter_end_snapshot_available_at_filing"
