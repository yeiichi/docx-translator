#!/usr/bin/env python3
"""
High-level DOCX translator (Tier-1: DeepL only).

Responsibilities:
- Orchestrate:
    DOCX → segments → engine.translate → DOCX
- Keep segmentation configurable (run-level or paragraph-level)
- Remain engine-agnostic (DeepL for Tier-1, others can be added)
- Preserve segment ordering so layout-preserving IO layer can do its job.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Protocol, runtime_checkable

from ..engines.deepl_engine.engine import DeepLEngine
from ..io.docx_reader import read_docx_to_segments
from ..io.docx_writer import write_segments_to_docx


logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Engine abstraction (for future: Google, etc.)
# --------------------------------------------------------------------------- #

@runtime_checkable
class TranslationEngine(Protocol):
    """
    Minimal protocol for translation engines.

    Tier-1: implemented by DeepLEngine only.
    Tier-2+: Google, Azure, OpenAI, etc. can conform to the same interface.
    """

    def translate_segments(
        self,
        segments: Sequence[str],
        source_lang: str,
        target_lang: str,
    ) -> List[str]:
        ...


# --------------------------------------------------------------------------- #
# Job dataclass
# --------------------------------------------------------------------------- #

@dataclass
class TranslationJob:
    """
    Simple config object for a single DOCX translation.

    input_path  : source DOCX
    output_path : translated DOCX
    source_lang : e.g. "EN"
    target_lang : e.g. "JA"
    """

    input_path: Path
    output_path: Path
    source_lang: str
    target_lang: str


# --------------------------------------------------------------------------- #
# Main high-level facade
# --------------------------------------------------------------------------- #

class DocxTranslator:
    """
    Facade class that ties together:

        - IO layer (DOCX reader / writer)
        - Translation engine (DeepLEngine for Tier-1)
        - Logging
        - Segmentation mode ("run" or "paragraph")

    Example:
        translator = DocxTranslator(segment_mode="paragraph")
        translator.translate_file("in.docx", "out.docx", "EN", "JA")
    """

    def __init__(
        self,
        engine: TranslationEngine | None = None,
        segment_mode: str = "run",   # "run" (default) or "paragraph"
    ) -> None:

        self.engine: TranslationEngine = engine or DeepLEngine()

        if segment_mode not in {"run", "paragraph"}:
            raise ValueError(f"Invalid segment_mode: {segment_mode}. "
                             f"Must be one of ['run', 'paragraph'].")

        self.segment_mode = segment_mode

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def run(self, job: TranslationJob) -> None:
        """
        Translate one DOCX file.

        Steps:
            1) Read DOCX → list of segments (text only)
            2) Translate segments via engine (DeepL)
            3) Write translated DOCX (layout preserved)
        """
        logger.info(
            "Starting translation: %s → %s (%s → %s)",
            job.input_path,
            job.output_path,
            job.source_lang,
            job.target_lang,
        )

        # 1. Extract segments using chosen segmentation mode
        segments = read_docx_to_segments(job.input_path, mode=self.segment_mode)
        logger.debug(
            "Extracted %d segments from %s (mode=%s)",
            len(segments),
            job.input_path,
            self.segment_mode,
        )

        if not segments:
            logger.warning(
                "No segments extracted from %s; copying document unchanged.",
                job.input_path,
            )
            write_segments_to_docx(
                input_path=job.input_path,
                output_path=job.output_path,
                translated_segments=[],
                mode=self.segment_mode,
            )
            return

        # 2. Translate via engine (DeepL + cache + dedupe)
        translated_segments = self.engine.translate_segments(
            segments=segments,
            source_lang=job.source_lang,
            target_lang=job.target_lang,
        )

        if len(translated_segments) != len(segments):
            raise RuntimeError(
                f"Segment length mismatch: expected {len(segments)}, "
                f"got {len(translated_segments)}"
            )

        logger.debug("Received %d translated segments", len(translated_segments))

        # 3. Write translated DOCX
        write_segments_to_docx(
            input_path=job.input_path,
            output_path=job.output_path,
            translated_segments=translated_segments,
            mode=self.segment_mode,
        )

        logger.info("Translation finished: %s", job.output_path)

    # ------------------------------------------------------------------ #
    # Convenience wrapper
    # ------------------------------------------------------------------ #

    def translate_file(
        self,
        input_path: str | Path,
        output_path: str | Path,
        source_lang: str,
        target_lang: str,
    ) -> None:
        """
        Convenience method so callers don't have to create TranslationJob.
        """
        job = TranslationJob(
            input_path=Path(input_path),
            output_path=Path(output_path),
            source_lang=source_lang,
            target_lang=target_lang,
        )
        self.run(job)
