from packages.gexy.regimes import classify_regime


def test_regime_classification() -> None:
    regime = classify_regime(spot=6500, total_gex=-10, gamma_flip=6501, iv=0.30, zero_dte=True)
    assert regime.gamma == "negative"
    assert regime.flip_bucket == "near_flip"
    assert regime.volatility == "high"
    assert regime.zero_dte is True
