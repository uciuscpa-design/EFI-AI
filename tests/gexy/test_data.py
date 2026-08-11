from datetime import datetime, timezone

from packages.gexy.data import OptionSnapshot, PriceSnapshot, synchronize


def test_synchronize_groups_exact_timestamps() -> None:
    ts = datetime(2026, 8, 10, 13, 30, tzinfo=timezone.utc)
    spx = [PriceSnapshot(ts, "SPX", 6500)]
    es = [PriceSnapshot(ts, "ES", 6501)]
    option = OptionSnapshot(
        timestamp=ts,
        contract_id="SPXW-6500-C",
        underlying="SPX",
        strike=6500,
        expiration=ts,
        option_type="call",
        gamma=0.01,
    )
    rows = synchronize(spx, es=es, options=[option])
    assert len(rows) == 1
    assert rows[0].es is not None
    assert len(rows[0].options) == 1
