"""PaperTrail configuration — shared settings object."""

from __future__ import annotations

from pathlib import Path


class Settings:
    """Runtime configuration for PaperTrail — all paths and tunables in one place."""

    DATA_DIR: Path = Path.cwd() / "data"
    DB_FILENAME: str = "papertrail.sqlite"
    MAX_CHUNK_SIZE: int = 90       # words per knowledge chunk
    MAX_SEARCH_TOKENS: int = 12    # max FTS5 query terms
    OCR_ENABLED: bool = True       # set False to skip Tesseract on low-resource machines
    SUPPORTED_PLAN_EXTENSIONS: frozenset = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff"})

    @property
    def db_path(self) -> Path:
        return self.DATA_DIR / self.DB_FILENAME

    @property
    def upload_dir(self) -> Path:
        p = self.DATA_DIR / "uploads"
        p.mkdir(parents=True, exist_ok=True)
        return p
