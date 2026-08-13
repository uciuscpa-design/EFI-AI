from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

from .gax_shadow_journal import load_gax_shadows, summarize_gax_shadow
from .prediction_journal import load_entries


def build_gax_shadow_report(
    prediction_journal: str | Path,
    gax_shadow_journal: str | Path,
) -> dict[str, object]:
    entries = load_entries(prediction_journal)
    shadows = load_gax_shadows(gax_shadow_journal)

    overall = summarize_gax_shadow(entries, shadows)
    horizons = sorted({shadow.horizon_minutes for shadow in shadows})
    versions = sorted({shadow.model_version for shadow in shadows})

    by_horizon: dict[str, dict[str, object]] = {}
    for horizon in horizons:
        horizon_entries = [
            entry for entry in entries if entry.prediction.horizon_minutes == horizon
        ]
        horizon_shadows = [
            shadow for shadow in shadows if shadow.horizon_minutes == horizon
        ]
        by_horizon[str(horizon)] = asdict(
            summarize_gax_shadow(horizon_entries, horizon_shadows)
        )

    by_model_version: dict[str, dict[str, object]] = {}
    for version in versions:
        version_entries = [entry for entry in entries if entry.model_version == version]
        version_shadows = [shadow for shadow in shadows if shadow.model_version == version]
        by_model_version[version] = asdict(
            summarize_gax_shadow(version_entries, version_shadows)
        )

    return {
        "prediction_journal_path": str(Path(prediction_journal)),
        "gax_shadow_journal_path": str(Path(gax_shadow_journal)),
        "overall": asdict(overall),
        "by_horizon": by_horizon,
        "by_model_version": by_model_version,
    }
