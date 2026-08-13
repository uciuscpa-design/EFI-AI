from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from .gax_shadow_candidate import score_shadow_candidate
from .gax_shadow_journal import GAXShadowRecord
from .prediction_journal import PredictionJournalEntry


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
