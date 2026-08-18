from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

from packages.gexy.baseline import (
    STATIONARY_FEATURES,
    fit_stationary_ridge,
    prepare_baseline_frame,
    purged_chronological_split,
)


def _parse_horizons(value: str) -> tuple[int, ...]:
    horizons = tuple(sorted({int(item.strip()) for item in value.split(",") if item.strip()}))
    if not horizons or any(item < 1 for item in horizons):
        raise argparse.ArgumentTypeError("horizons must be positive comma-separated minutes")
    return horizons


def _safe_corr(left: pd.Series, right: pd.Series) -> float | None:
    a = pd.to_numeric(left, errors="coerce")
    b = pd.to_numeric(right, errors="coerce")
    mask = a.notna() & b.notna()
    if mask.sum() < 3:
        return None
    av = a[mask].to_numpy(dtype=float)
    bv = b[mask].to_numpy(dtype=float)
    if np.std(av) <= 0 or np.std(bv) <= 0:
        return None
    return float(np.corrcoef(av, bv)[0, 1])


def _target_stats(series: pd.Series) -> dict[str, float]:
    values = pd.to_numeric(series, errors="coerce").dropna().to_numpy(dtype=float)
    if len(values) == 0:
        return {
            "mean": float("nan"),
            "median": float("nan"),
            "std": float("nan"),
            "mean_abs": float("nan"),
            "positive_pct": float("nan"),
        }
    return {
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "std": float(np.std(values)),
        "mean_abs": float(np.mean(np.abs(values))),
        "positive_pct": float(np.mean(values > 0)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose GEXY stationary-baseline regime shift without changing the model. "
            "Reports train/test target drift, prediction saturation, feature drift, and "
            "train-vs-test univariate correlation stability."
        )
    )
    parser.add_argument("--features-csv", required=True, type=Path)
    parser.add_argument("--horizons", type=_parse_horizons, default=(1, 5, 15, 30, 60))
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--alpha", type=float, default=25.0)
    parser.add_argument("--prediction-quantile", type=float, default=0.99)
    parser.add_argument("--top", type=int, default=8)
    args = parser.parse_args()

    raw = pd.read_csv(args.features_csv)
    raw["timestamp"] = pd.to_datetime(raw["timestamp"], utc=True, errors="coerce")
    if "backward_return_1m_bps" not in raw.columns and "forward" in raw.columns:
        current = pd.to_numeric(raw["forward"], errors="coerce")
        raw["backward_return_1m_bps"] = (current / current.shift(1) - 1.0) * 10_000.0

    summary_rows: list[dict[str, object]] = []
    drift_rows: list[dict[str, object]] = []

    print(f"INPUT FEATURE ROWS: {len(raw)}")
    print(f"HORIZONS: {','.join(str(item) for item in args.horizons)} minutes")
    print("DIAGNOSTIC ONLY: no feature selection or tuning is performed on the test block")

    for horizon in args.horizons:
        prepared, features, target = prepare_baseline_frame(
            raw,
            horizon_minutes=horizon,
            feature_candidates=STATIONARY_FEATURES,
        )
        split = purged_chronological_split(
            prepared,
            horizon_minutes=horizon,
            train_fraction=args.train_fraction,
        )
        model = fit_stationary_ridge(
            split.train,
            features=features,
            target=target,
            alpha=args.alpha,
            prediction_quantile=args.prediction_quantile,
        )

        train_target = pd.to_numeric(split.train[target], errors="coerce")
        test_target = pd.to_numeric(split.test[target], errors="coerce")
        prediction = model.predict(split.test)

        train_stats = _target_stats(train_target)
        test_stats = _target_stats(test_target)
        pred_stats = _target_stats(pd.Series(prediction))

        ceiling = abs(float(model.prediction_ceiling or 0.0))
        saturation_pct = (
            float(np.mean(np.abs(prediction) >= ceiling * 0.999)) if ceiling > 0 else 0.0
        )
        sign_bias = float(np.mean(np.sign(prediction))) if len(prediction) else float("nan")
        pred_to_actual_abs = (
            pred_stats["mean_abs"] / test_stats["mean_abs"]
            if test_stats["mean_abs"] > 0
            else float("nan")
        )

        horizon_drift_rows: list[dict[str, object]] = []
        for feature in model.features:
            train_values = pd.to_numeric(split.train[feature], errors="coerce")
            test_values = pd.to_numeric(split.test[feature], errors="coerce")
            train_median = float(train_values.median()) if train_values.notna().any() else float("nan")
            test_median = float(test_values.median()) if test_values.notna().any() else float("nan")
            scale = float(model.scales[feature])
            median_shift_scales = (
                (test_median - train_median) / scale
                if np.isfinite(train_median) and np.isfinite(test_median) and scale > 0
                else float("nan")
            )
            train_q01 = float(train_values.quantile(0.01)) if train_values.notna().any() else float("nan")
            train_q99 = float(train_values.quantile(0.99)) if train_values.notna().any() else float("nan")
            outside = (
                ((test_values < train_q01) | (test_values > train_q99)).mean()
                if np.isfinite(train_q01) and np.isfinite(train_q99)
                else float("nan")
            )
            train_corr = _safe_corr(split.train[feature], train_target)
            test_corr = _safe_corr(split.test[feature], test_target)
            corr_flip = (
                bool(train_corr * test_corr < 0)
                if train_corr is not None and test_corr is not None
                else False
            )
            coefficient = float(model.standardized_coefficients()[feature])
            row = {
                "horizon_minutes": horizon,
                "feature": feature,
                "coefficient": coefficient,
                "median_shift_train_scales": median_shift_scales,
                "test_outside_train_1_99_pct": float(outside) if np.isfinite(outside) else float("nan"),
                "train_univariate_corr": train_corr,
                "test_univariate_corr": test_corr,
                "correlation_sign_flip": corr_flip,
            }
            horizon_drift_rows.append(row)
            drift_rows.append(row)

        drift_frame = pd.DataFrame(horizon_drift_rows)
        if not drift_frame.empty:
            worst_shift = drift_frame.loc[
                drift_frame["median_shift_train_scales"].abs().idxmax()
            ]
            sign_flips = int(drift_frame["correlation_sign_flip"].sum())
            max_abs_shift = float(drift_frame["median_shift_train_scales"].abs().max())
        else:
            worst_shift = None
            sign_flips = 0
            max_abs_shift = float("nan")

        summary_rows.append(
            {
                "horizon_minutes": horizon,
                "train_rows": len(split.train),
                "test_rows": len(split.test),
                "train_target_mean_bps": train_stats["mean"],
                "test_target_mean_bps": test_stats["mean"],
                "train_target_mean_abs_bps": train_stats["mean_abs"],
                "test_target_mean_abs_bps": test_stats["mean_abs"],
                "train_target_positive_pct": train_stats["positive_pct"],
                "test_target_positive_pct": test_stats["positive_pct"],
                "prediction_mean_bps": pred_stats["mean"],
                "prediction_mean_abs_bps": pred_stats["mean_abs"],
                "prediction_to_actual_abs_ratio": pred_to_actual_abs,
                "prediction_saturation_pct": saturation_pct,
                "prediction_sign_bias": sign_bias,
                "max_feature_median_shift_scales": max_abs_shift,
                "feature_corr_sign_flips": sign_flips,
                "worst_shift_feature": None if worst_shift is None else str(worst_shift["feature"]),
            }
        )

        print(f"\nHORIZON {horizon}m")
        print(
            f"TARGET MEAN train/test: {train_stats['mean']:+.3f} / {test_stats['mean']:+.3f} bps"
        )
        print(
            f"TARGET |RETURN| train/test: {train_stats['mean_abs']:.3f} / {test_stats['mean_abs']:.3f} bps"
        )
        print(
            f"TARGET POSITIVE train/test: {train_stats['positive_pct']:.1%} / {test_stats['positive_pct']:.1%}"
        )
        print(
            f"PREDICTION mean/|mean|: {pred_stats['mean']:+.3f} / {pred_stats['mean_abs']:.3f} bps"
        )
        print(f"PREDICTION / ACTUAL ABS RATIO: {pred_to_actual_abs:.2f}x")
        print(f"PREDICTIONS AT CAP: {saturation_pct:.1%}")
        print(f"FEATURE CORRELATION SIGN FLIPS: {sign_flips}/{len(model.features)}")
        if worst_shift is not None:
            print(
                "WORST MEDIAN FEATURE SHIFT: "
                f"{worst_shift['feature']} = {worst_shift['median_shift_train_scales']:+.2f} train-scales"
            )
        print("TOP FEATURE DRIFT")
        if not drift_frame.empty:
            ranked = drift_frame.assign(
                abs_shift=drift_frame["median_shift_train_scales"].abs()
            ).sort_values("abs_shift", ascending=False)
            for _, row in ranked.head(args.top).iterrows():
                tr = row["train_univariate_corr"]
                te = row["test_univariate_corr"]
                tr_text = "n/a" if pd.isna(tr) else f"{tr:+.3f}"
                te_text = "n/a" if pd.isna(te) else f"{te:+.3f}"
                print(
                    f"  {row['feature']}: shift={row['median_shift_train_scales']:+.2f} "
                    f"outside={row['test_outside_train_1_99_pct']:.1%} "
                    f"corr train/test={tr_text}/{te_text}"
                )

    summary = pd.DataFrame(summary_rows)
    drift = pd.DataFrame(drift_rows)
    stem = args.features_csv.stem
    summary_path = args.features_csv.with_name(f"{stem}_stationary_diagnostics_summary.csv")
    drift_path = args.features_csv.with_name(f"{stem}_stationary_feature_drift.csv")
    summary.to_csv(summary_path, index=False)
    drift.to_csv(drift_path, index=False)

    print("\nDIAGNOSTIC SUMMARY")
    display = [
        "horizon_minutes",
        "train_target_mean_bps",
        "test_target_mean_bps",
        "prediction_mean_abs_bps",
        "prediction_to_actual_abs_ratio",
        "prediction_saturation_pct",
        "max_feature_median_shift_scales",
        "feature_corr_sign_flips",
        "worst_shift_feature",
    ]
    print(summary[display].to_string(index=False))
    print(f"\nSAVED SUMMARY: {summary_path}")
    print(f"SAVED FEATURE DRIFT: {drift_path}")
    print(
        "NOTE: Test correlations are diagnostic only and must not be used to choose features "
        "or tune the model on this session."
    )


if __name__ == "__main__":
    main()
