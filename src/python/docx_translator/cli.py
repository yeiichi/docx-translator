#!/usr/bin/env python3
"""
Command-line interface for docx-translator (DeepL-based).

This CLI focuses on two main workflows:

- Translating a single DOCX file (translate).
- Translating all DOCX files in a directory (translate-dir).

DeepL endpoint selection
------------------------

By default, the CLI uses the Free DeepL API endpoint
(https://api-free.deepl.com). You can switch to the Pro endpoint by
passing --pro. The choice is forwarded to the HTTP client via the
DEEPL_API_URL environment variable:

- --free → DEEPL_API_URL=https://api-free.deepl.com/v2/translate
- --pro  → DEEPL_API_URL=https://api.deepl.com/v2/translate

If you set DEEPL_API_URL yourself, it will be overwritten when you pass
--free or --pro explicitly.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from docx_translator.core.translator import DocxTranslator

LOGGER = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Logging and DeepL endpoint configuration
# --------------------------------------------------------------------------- #
def _setup_logging(verbosity: int, quiet: bool) -> None:
    """
    Logging behavior:
      quiet = True → ERROR only
      verbosity = 0 → INFO  (default)
      verbosity >= 1 → DEBUG
    """
    if quiet:
        level = logging.ERROR
    else:
        if verbosity <= 0:
            level = logging.INFO
        else:
            level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )


def _configure_deepl_endpoint(plan: str) -> None:
    """
    Set DEEPL_API_URL based on the requested DeepL plan.

    Parameters
    ----------
    plan:
        Either "free" or "pro".
    """
    if plan == "pro":
        api_url = "https://api.deepl.com/v2/translate"
    else:
        api_url = "https://api-free.deepl.com/v2/translate"

    os.environ["DEEPL_API_URL"] = api_url
    LOGGER.info("Using DeepL %s endpoint: %s", plan, api_url)


def _add_common_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity. 0=info (default), 1+=debug."
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Quiet mode: only errors are shown."
    )


def _add_deepl_plan_options(parser: argparse.ArgumentParser) -> None:
    """Add --free / --pro options to a subcommand parser."""
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--free",
        dest="deepl_plan",
        action="store_const",
        const="free",
        help="Use DeepL Free API (api-free.deepl.com) [default].",
    )
    group.add_argument(
        "--pro",
        dest="deepl_plan",
        action="store_const",
        const="pro",
        help="Use DeepL Pro API (api.deepl.com).",
    )
    # Default plan
    parser.set_defaults(deepl_plan="free")


# --------------------------------------------------------------------------- #
# Commands
# --------------------------------------------------------------------------- #
def cmd_translate(args: argparse.Namespace) -> int:
    """Translate a single DOCX file."""
    _setup_logging(args.verbose, args.quiet)
    _configure_deepl_endpoint(args.deepl_plan)

    translator = DocxTranslator()

    src_path = Path(args.input)
    dst_path = Path(args.output)

    LOGGER.info(
        "Translating single file: %s → %s (%s → %s)",
        src_path,
        dst_path,
        args.source,
        args.target,
    )

    try:
        translator.translate_file(
            input_path=src_path,
            output_path=dst_path,
            source_lang=args.source,
            target_lang=args.target,
        )
    except Exception as exc:  # defensive
        LOGGER.error("Translation failed: %s", exc)
        return 1

    LOGGER.info("Done.")
    return 0


def _iter_docx_files(root: Path, recursive: bool = False) -> List[Path]:
    """Return a sorted list of DOCX files under root."""
    if recursive:
        files = sorted(p for p in root.rglob("*.docx") if p.is_file())
    else:
        files = sorted(p for p in root.glob("*.docx") if p.is_file())
    return files


def cmd_translate_dir(args: argparse.Namespace) -> int:
    """Translate all DOCX files in a directory."""
    _setup_logging(args.verbose, args.quiet)
    _configure_deepl_endpoint(args.deepl_plan)

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    recursive = args.recursive

    # Validate input directory before constructing the translator / engine.
    if not input_dir.exists() or not input_dir.is_dir():
        LOGGER.error(
            "Input directory does not exist or is not a directory: %s",
            input_dir,
        )
        return 1

    # Ensure output directory exists.
    output_dir.mkdir(parents=True, exist_ok=True)

    files = _iter_docx_files(input_dir, recursive=recursive)
    if not files:
        LOGGER.warning(
            "No DOCX files found in %s (recursive=%s)",
            input_dir,
            recursive,
        )
        return 0

    LOGGER.info(
        "Found %d DOCX file(s) in %s (recursive=%s)",
        len(files),
        input_dir,
        recursive,
    )
    LOGGER.info(
        "Output directory: %s | Languages: %s → %s",
        output_dir,
        args.source,
        args.target,
    )

    # Construct the translator only after we've validated inputs.
    translator = DocxTranslator()

    total = len(files)
    for idx, src_path in enumerate(files, start=1):
        # eur_15_2025Q4_tracker.docx -> eur_15_2025Q4_tracker.ja.docx (for JA)
        target_suffix = args.target.lower()
        dst_name = f"{src_path.stem}.{target_suffix}.docx"
        dst_path = output_dir / dst_name

        # Skip existing outputs unless --overwrite was given.
        if dst_path.exists() and not getattr(args, "overwrite", False):
            LOGGER.info(
                "[%d/%d] Skipping existing file (use --overwrite to replace): %s",
                idx,
                total,
                dst_path,
            )
            continue

        LOGGER.info(
            "[%d/%d] Translating %s -> %s",
            idx,
            total,
            src_path.name,
            dst_name,
        )

        try:
            translator.translate_file(
                input_path=src_path,
                output_path=dst_path,
                source_lang=args.source,
                target_lang=args.target,
            )
        except Exception as exc:  # defensive
            LOGGER.error(
                "[%d/%d] Translation failed for %s: %s",
                idx,
                total,
                src_path,
                exc,
            )

    LOGGER.info("Batch translation complete.")
    return 0


# --------------------------------------------------------------------------- #
# Argument parser
# --------------------------------------------------------------------------- #
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="docx-translator",
        description="Translate DOCX files using DeepL.",
    )

    subparsers = parser.add_subparsers(
        title="subcommands",
        dest="command",
        metavar="<command>",
    )

    # Global options shared by all subcommands
    _add_common_options(parser)

    # translate (single file)
    p_translate = subparsers.add_parser(
        "translate",
        help="Translate a single DOCX file.",
    )
    p_translate.add_argument(
        "-s",
        "--source",
        required=True,
        help="Source language code (for example EN).",
    )
    p_translate.add_argument(
        "-t",
        "--target",
        required=True,
        help="Target language code (for example JA).",
    )
    p_translate.add_argument(
        "input",
        metavar="INPUT",
        help="Input DOCX file.",
    )
    p_translate.add_argument(
        "output",
        metavar="OUTPUT",
        help="Output DOCX file.",
    )
    _add_deepl_plan_options(p_translate)
    p_translate.set_defaults(func=cmd_translate)

    # translate-dir (batch)
    p_translate_dir = subparsers.add_parser(
        "translate-dir",
        help="Translate all DOCX files in a directory.",
    )
    p_translate_dir.add_argument(
        "-s",
        "--source",
        required=True,
        help="Source language code (for example EN).",
    )
    p_translate_dir.add_argument(
        "-t",
        "--target",
        required=True,
        help="Target language code (for example JA).",
    )
    p_translate_dir.add_argument(
        "-i",
        "--input-dir",
        required=True,
        help="Input directory containing DOCX files.",
    )
    p_translate_dir.add_argument(
        "-o",
        "--output-dir",
        required=True,
        help="Output directory for translated DOCX files.",
    )
    p_translate_dir.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Recursively search for DOCX files in input directory.",
    )
    p_translate_dir.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing output files instead of skipping them.",
    )
    _add_deepl_plan_options(p_translate_dir)
    p_translate_dir.set_defaults(func=cmd_translate_dir)

    return parser


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #
def main(argv: Optional[Iterable[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(list(argv))

    if not hasattr(args, "func"):
        parser.print_help()
        return 1

    return args.func(args)


if __name__ == "__main__":  # CLI entry
    raise SystemExit(main())
