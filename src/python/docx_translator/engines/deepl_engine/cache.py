#!/usr/bin/env python3
"""
DeepL translation cache.

Key points:
- Uses SHA-256 over (source_lang, target_lang, text) for keys.
- Stores a simple JSON file on disk.
- Designed to reduce DeepL API calls for repeated segments.
"""

from __future__ import annotations

import json
import hashlib
import threading
from pathlib import Path
from typing import Dict, Optional


def _default_cache_dir() -> Path:
    """
    Default cache directory:
    <project_root>/src/python/docx_translator/storage/cache

    This assumes this file lives under:
    src/python/docx_translator/engines/deepl_engine/cache.py
    """
    # engines/deepl_engine/cache.py -> deepl_engine -> engines -> docx_translator -> python -> src -> project_root
    # parents: [cache.py, deepl_engine, engines, docx_translator, python, src, project_root]
    return Path(__file__).resolve().parents[3] / "storage" / "cache"


def make_hash(source_lang: str, target_lang: str, text: str) -> str:
    """
    Build a SHA-256 digest for (source_lang, target_lang, text).

    This makes the cache safe across different language pairs.
    """
    key = f"{source_lang.upper()}|{target_lang.upper()}|{text}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


class TranslationCache:
    """
    Very simple JSON-based translation cache.

    Structure of json:
        {
          "<sha256>": "<translated_text>",
          ...
        }

    Not optimized for huge scale, but perfectly fine for typical
    DOCX translation workloads.
    """

    def __init__(self, cache_dir: Optional[Path | str] = None, filename: str = "deepl_cache.json") -> None:
        if cache_dir is None:
            cache_dir = _default_cache_dir()
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_path = self.cache_dir / filename

        self._lock = threading.Lock()
        self._data: Dict[str, str] = {}
        self._loaded = False

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _load(self) -> None:
        if self._loaded:
            return
        with self._lock:
            if self._loaded:
                return
            if self.cache_path.is_file():
                try:
                    self._data = json.loads(self.cache_path.read_text(encoding="utf-8"))
                except Exception:
                    # If cache is broken, start fresh but do not crash.
                    self._data = {}
            self._loaded = True

    def _save(self) -> None:
        with self._lock:
            tmp_path = self.cache_path.with_suffix(".tmp")
            tmp_path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self.cache_path)

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def get(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        """
        Return cached translation if present; otherwise None.
        """
        self._load()
        digest = make_hash(source_lang, target_lang, text)
        return self._data.get(digest)

    def set(self, text: str, translated: str, source_lang: str, target_lang: str) -> None:
        """
        Store translation in cache (overwrites if same key exists).
        """
        self._load()
        digest = make_hash(source_lang, target_lang, text)
        self._data[digest] = translated
        self._save()

    def bulk_set(self, mapping: Dict[str, str], source_lang: str, target_lang: str) -> None:
        """
        Store many translations at once.

        mapping: {original_text: translated_text}
        """
        if not mapping:
            return
        self._load()
        for original, translated in mapping.items():
            digest = make_hash(source_lang, target_lang, original)
            self._data[digest] = translated
        self._save()
