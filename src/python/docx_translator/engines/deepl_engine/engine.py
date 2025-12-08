#!/usr/bin/env python3
"""
DeepL engine adaptor.

This module connects:
  - High-level segment list (from DOCX)
  - Translation cache (to avoid redundant calls)
  - DeepL HTTP client (for actual translations)

Key design goals:
  - Preserve the order of input segments → caller can map them back
    to DOCX structure and layout.
  - Deduplicate segments before hitting the API.
  - Use a persistent cache keyed by (src_lang, tgt_lang, text).
"""

from __future__ import annotations

import logging
from typing import List, Sequence, Dict

from .cache import TranslationCache
from .client import DeepLClient

logger = logging.getLogger(__name__)


class DeepLEngine:
    """
    High-level engine for DeepL-backed translation.

    Typical usage:
        engine = DeepLEngine()
        translated_segments = engine.translate_segments(segments, "EN", "JA")

    This engine is intentionally text-only: it does not know anything
    about DOCX. Layout preservation is achieved by:
      - Calling translate_segments() with a *flat* ordered list of
        segments (extracted from DOCX).
      - Receiving a list with the *same length and order*.
      - Higher layers then reassign each translated segment back to
        its original paragraph/run/table cell, etc.
    """

    def __init__(
            self,
            client: DeepLClient | None = None,
            cache: TranslationCache | None = None,
            max_batch_size: int = 50,
    ) -> None:
        self.client = client or DeepLClient()
        self.cache = cache or TranslationCache()
        self.max_batch_size = max_batch_size

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def translate_segments(
            self,
            segments: Sequence[str],
            source_lang: str,
            target_lang: str,
    ) -> List[str]:
        """
        Translate a sequence of segments (strings) with DeepL.

        - Preserves original order.
        - Leverages cache.
        - Dedupe identical uncached segments to minimize API cost.
        - Sends requests in batches of `max_batch_size`.

        Empty strings are returned as-is and never sent to the API.
        """
        if not segments:
            return []

        n = len(segments)
        result: List[str | None] = [None] * n

        cache_hits = 0
        cache_miss_slots = 0

        # 1. First pass: use cache and build list of uncached segments
        #    (dedup by text).
        unique_to_translate: List[str] = []
        text_to_indices: Dict[str, List[int]] = {}

        for idx, text in enumerate(segments):
            if not text:
                # Keep exact empty string; no translation needed
                result[idx] = ""
                continue

            cached = self.cache.get(text, source_lang, target_lang)
            if cached is not None:
                result[idx] = cached
                cache_hits += 1
                continue

            cache_miss_slots += 1

            # Not cached → mark for translation, but dedupe by text
            if text not in text_to_indices:
                text_to_indices[text] = []
                unique_to_translate.append(text)
            text_to_indices[text].append(idx)

        # If everything came from cache, we're done
        if not unique_to_translate:
            logger.info(
                "DeepLEngine: total=%d, cache_hits=%d, cache_miss_slots=%d, unique_to_translate=0, batches=0",
                n,
                cache_hits,
                cache_miss_slots,
            )
            return [r if r is not None else "" for r in result]

        # 2. Call DeepL in batches for the unique uncached segments
        translated_map: Dict[str, str] = {}
        num_batches = 0

        for batch_start in range(0, len(unique_to_translate), self.max_batch_size):
            batch = unique_to_translate[batch_start: batch_start + self.max_batch_size]
            translated_batch = self.client.translate_texts(batch, source_lang, target_lang)

            if len(translated_batch) != len(batch):
                raise RuntimeError(
                    f"DeepL batch translation length mismatch "
                    f"(input={len(batch)}, output={len(translated_batch)})"
                )

            for original, translated in zip(batch, translated_batch):
                translated_map[original] = translated

            num_batches += 1

        # 3. Fill result array and update cache
        self.cache.bulk_set(translated_map, source_lang, target_lang)

        for original, translated in translated_map.items():
            for idx in text_to_indices.get(original, []):
                result[idx] = translated

        # 4. Sanity: every element should now be non-None
        final: List[str] = []
        for idx, value in enumerate(result):
            if value is None:
                raise RuntimeError(f"Missing translation for segment index {idx}")
            final.append(value)

        logger.info(
            "DeepLEngine: total=%d, cache_hits=%d, cache_miss_slots=%d, unique_to_translate=%d, batches=%d",
            n,
            cache_hits,
            cache_miss_slots,
            len(unique_to_translate),
            num_batches,
        )

        return final
