from packages.gexy.backtest import chronological_split


def test_split_preserves_time_order() -> None:
    result = chronological_split(list(range(10)), train_fraction=0.6, validation_fraction=0.2)
    assert result.train == [0, 1, 2, 3, 4, 5]
    assert result.validation == [6, 7]
    assert result.test == [8, 9]
