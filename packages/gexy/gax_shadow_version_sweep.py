from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Iterable

from .gax_shadow_candidate import score_shadow_candidate
from .gax_shadow_journal import GAXShadowRecord, load_gax_shadows
from .prediction_journal import PredictionJournalEntry, load_entries


DEFAULT_SHADOW_THRESHOLDS = (0.0, 0.5, 1.0, 2.0)


def build_shadow_candidate_sweep_by_model_version(
    entries: Iterable[PredictionJournalEntry],
    shadows: Iterable[GAXShadowRecord],
) -> dict[str, dict[str, dict[str, object]]]:
    entry_list = list(entries)
    shadow_list = list(shadows)
    versions = sorted({shadow.model_version for shadow in shadow_list})
    report: dict[str, dict[str, dict[str, object]]] = {}

    for version in versions:
        version_entries = [entry for entry in entry_list if entry.model_version == version]
        version_shadows = [shadow for shadow in shadow_list if shadow.model_version == version]
        report[version] = {
            str(threshold): asdict(
                score_shadow_candidate(
                    version_entries,
                    version_shadows,
                    min_gax_magnitude=threshold,
                )
            )
            for threshold in DEFAULT_SHADOW_THRESHOLDS
        }

    return report


def build_consolidated_shadow_v2_report(
    prediction_journal: str | Path,
    gax_shadow_journal: str | Path,
) -> dict[str, object]:
    """Compose the existing GAX shadow report with per-version v2 sweeps.

    This is read-only evaluation. It never changes production predictions or
    promotes GAX into the live model.
    """
    from .gax_shadow_report import build_gax_shadow_report

    entries = load_entries(prediction_journal)
    shadows = load_gax_shadows(gax_shadow_journal)
    report = build_gax_shadow_report(prediction_journal, gax_shadow_journal)
    report["shadow_candidate_threshold_sweep_by_model_version"] = (
        build_shadow_candidate_sweep_by_model_version(entries, shadows)
    )
    return report
