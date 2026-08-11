from packages.gexy.calibration import make_label, score_forecasts


def test_make_label_and_score() -> None:
    labels = [make_label(6500, 6505, 5), make_label(6500, 6498, 5)]
    metrics = score_forecasts([0.8, 0.2], [5, -2], labels)
    assert metrics.samples == 2
    assert metrics.directional_accuracy == 1.0
    assert metrics.mean_absolute_error == 0.0
    assert metrics.brier_score < 0.05
