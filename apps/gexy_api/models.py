from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from packages.gexy.model import LinearModel


@dataclass(frozen=True)
class ModelBundle:
    version: str
    trained_through: datetime
    models: Mapping[int, LinearModel]


class ModelRegistry:
    def __init__(self, bundle: ModelBundle | None = None) -> None:
        self._bundle = bundle

    def load(self, bundle: ModelBundle) -> None:
        if not bundle.version:
            raise ValueError("model version is required")
        if not bundle.models:
            raise ValueError("at least one horizon model is required")
        self._bundle = bundle

    def current(self) -> ModelBundle:
        if self._bundle is None:
            raise RuntimeError("no model bundle loaded")
        return self._bundle
