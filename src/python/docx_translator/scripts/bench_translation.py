#!/usr/bin/env python3
"""
Batch DOCX translator using DeepL (Tier-1).

Usage examples
--------------

# Translate all DOCX files under ./in_docs to ./out_docs
python -m docx_translator.scripts.bench_translation \
    --src EN --tgt JA \
    --input-dir in_docs \
    --output-dir out_docs

# Recursive, preserve structure, and add suffix
python -m docx_translator.scripts.bench_translation \
    --src EN --tgt DE \
    --input-dir in_docs \
    --output-dir out_docs \
    --recursive \
    --suffix _de
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import List

from docx_translator.core.translator import DocxTranslator


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_docx_files(input_dir: Path, recursive: bool) -> List[Path]:
    """
    Find .docx files under `input_dir`.

    - Skips Microsoft Office temporary lock-files starting with "~$"
    - Uses glob/rglob depending on `recursive`
    """
    pattern = "**/*.docx" if recursive else "*.docx"

    files = [
        p for p in input_dir.glob(pattern)
        if p.is_file() and not p.name.startswith("~$")
    ]
    return sorted(files)


# ---------------------------------------------------------------------------
# Output path computation
# ---------------------------------------------------------------------------

def compute_output_path(
    in_file: Path,
    input_dir: Path,
    output_dir: Path,
    suffix: str,
) -> Path:
    """
    Build output path by:

      - Preserving directory structure relative to input_dir
      - Adding suffix before ".docx"
      - Always writing to output_dir

    Example:
        input_dir = in_docs/
        file = in_docs/foo/bar.docx
        suffix = "_ja"

        → out_docs/foo/bar_ja.docx
    """
    rel = in_file.relative_to(input_dir)
    stem = rel.stem + suffix
    out_rel = rel.with_name(stem).with_suffix(".docx")
    return output_dir / out_rel


# ---------------------------------------------------------------------------
# Batch runner core logic
# ---------------------------------------------------------------------------

def translate_batch(
    src_lang: str,
    tgt_lang: str,
    input_dir: Path,
    output_dir: Path,
    recursive: bool,
    suffix: str,
    overwrite: bool,
    verbose: bool,
    segment_mode: str = "run",
) -> int:
    """
    Execute batch translation.

    src_lang    : "EN"
    tgt_lang    : "JA"
    input_dir   : directory with input .docx
    output_dir  : where translated .docx will be written
    recursive   : whether to search subdirectories
    suffix      : e.g. "_ja" or "_de"
    overwrite   : overwrite existing outputs
    verbose     : verbose logging
    segment_mode: "run" or "paragraph"
    """
    _setup_logging(verbose)

    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("Batch translation start")
    logger.info(" Source lang: %s", src_lang)
    logger.info(" Target lang: %s", tgt_lang)
    logger.info(" Input dir  : %s", input_dir)
    logger.info(" Output dir : %s", output_dir)
    logger.info(" Recursive  : %s", recursive)
    logger.info(" Suffix     : %s", suffix)
    logger.info(" Overwrite  : %s", overwrite)
    logger.info(" Segment    : %s", segment_mode)

    files = find_docx_files(input_dir, recursive=recursive)
    if not files:
        logger.warning("No .docx files found under %s", input_dir)
        return 0

    logger.info("Found %d .docx file(s) to process", len(files))

    translator = DocxTranslator(segment_mode=segment_mode)

    num_ok = 0
    num_skip = 0
    num_err = 0

    for in_file in files:
        out_file = compute_output_path(
            in_file=in_file,
            input_dir=input_dir,
            output_dir=output_dir,
            suffix=suffix,
        )

        # Ensure nested dirs exist
        out_file.parent.mkdir(parents=True, exist_ok=True)

        # Skip if file exists and not overwriting
        if out_file.exists() and not overwrite:
            logger.info("SKIP (exists): %s -> %s", in_file, out_file)
            num_skip += 1
            continue

        # Process document
        try:
            logger.info("Translating: %s -> %s", in_file, out_file)
            translator.translate_file(
                input_path=in_file,
                output_path=out_file,
                source_lang=src_lang,
                target_lang=tgt_lang,
            )
            num_ok += 1
        except Exception as exc:  # noqa: BLE001
            logger.error("FAILED: %s -> %s (%s)", in_file, out_file, exc)
            num_err += 1

    logger.info("Batch translation done")
    logger.info(" OK   : %d", num_ok)
    logger.info(" SKIP : %d", num_skip)
    logger.info(" ERROR: %d", num_err)

    return 0 if num_err == 0 else 1


# ---------------------------------------------------------------------------
# CLI parser
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docx-translator-bench",
        description="Batch DOCX translator using DeepL (Tier-1).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging.",
    )
    parser.add_argument(
        "--src",
        "--source",
        dest="src",
        required=True,
        help="Source language code (e.g. EN, JA, DE).",
    )
    parser.add_argument(
        "--tgt",
        "--target",
        dest="tgt",
        required=True,
        help="Target language code (e.g. JA, EN).",
    )
    parser.add_argument(
        "--segment-level",
        choices=["run", "paragraph"],
        default="run",
        help="Segmentation level: 'run' (default, preserves formatting) or 'paragraph' (fewer API calls).",
    )
    parser.add_argument(
        "--input-dir",
        "-i",
        type=Path,
        required=True,
        help="Input directory containing .docx files.",
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        type=Path,
        required=True,
        help="Output directory for translated .docx files.",
    )
    parser.add_argument(
        "--recursive",
        "-r",
        action="store_true",
        help="Search input directory recursively.",
    )
    parser.add_argument(
        "--suffix",
        default=None,
        help="Suffix appended before .docx (default: _<tgt_lower>, e.g. _ja).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files.",
    )
    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    suffix = args.suffix or f"_{args.tgt.lower()}"

    return translate_batch(
        src_lang=args.src,
        tgt_lang=args.tgt,
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        recursive=args.recursive,
        suffix=suffix,
        overwrite=args.overwrite,
        verbose=args.verbose,
        segment_mode=args.segment_level,
    )


if __name__ == "__main__":
    raise SystemExit(main())
