from datetime import date

from scripts.gexy_multiday_replay import _parse_dates


def test_parse_dates_preserves_frozen_batch_order_and_deduplicates() -> None:
    parsed = _parse_dates("2026-08-03,2026-07-31,2026-07-30,2026-08-03")

    assert parsed == (
        date(2026, 8, 3),
        date(2026, 7, 31),
        date(2026, 7, 30),
    )
