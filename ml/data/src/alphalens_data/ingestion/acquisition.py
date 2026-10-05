"""Acquisition boundary alongside provider.py; parsing never calls a network."""

from pathlib import Path
from typing import Protocol


class ArtifactSource(Protocol):
    def acquire(self) -> bytes:
        """Return exact artifact bytes under the caller's verified retention rights."""


class LocalFileSource:
    def __init__(self, path: Path) -> None:
        self.path = path

    def acquire(self) -> bytes:
        return self.path.read_bytes()
