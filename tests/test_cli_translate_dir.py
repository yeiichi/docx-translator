from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from docx_translator import cli as cli_mod


class DummyTranslator:
    """
    Fake DocxTranslator for CLI-level tests.

    - Records calls to translate_file
    - Simply copies input -> output so the file exists.
    """

    def __init__(self) -> None:
        self.calls: list[tuple[Path, Path, str, str]] = []

    def translate_file(
            self,
            input_path: Path,
            output_path: Path,
            source_lang: str,
            target_lang: str,
    ) -> None:
        self.calls.append((input_path, output_path, source_lang, target_lang))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Just copy bytes; we don't care about real DOCX content here
        shutil.copy2(input_path, output_path)


@pytest.fixture
def dummy_translator(monkeypatch) -> DummyTranslator:
    """
    Replace DocxTranslator in the CLI module with DummyTranslator.

    This avoids calling real DeepL / external APIs.
    """
    dummy = DummyTranslator()

    def _ctor():
        return dummy

    # Patch the symbol that cli.py imported
    monkeypatch.setattr(cli_mod, "DocxTranslator", _ctor)
    return dummy


def test_translate_dir_basic(tmp_path: Path, dummy_translator: DummyTranslator) -> None:
    """
    Basic integration test for `translate-dir`.

    - Creates 2 dummy .docx files in an input directory
    - Runs the CLI
    - Checks that:
        - exit code is 0
        - outputs are created with default suffix = target.lower()
        - DummyTranslator.translate_file is called for each file
    """
    in_dir = tmp_path / "in_docs"
    out_dir = tmp_path / "out_docs"
    in_dir.mkdir()

    # Create dummy .docx files
    (in_dir / "a.docx").write_bytes(b"a-content")
    (in_dir / "b.docx").write_bytes(b"b-content")

    exit_code = cli_mod.main(
        [
            "translate-dir",
            "-s",
            "EN",
            "-t",
            "JA",
            "-i",
            str(in_dir),
            "-o",
            str(out_dir),
        ]
    )

    assert exit_code == 0

    # Default suffix is target.lower() => "ja"
    out_a = out_dir / "a.ja.docx"
    out_b = out_dir / "b.ja.docx"

    assert out_a.is_file()
    assert out_b.is_file()

    # Dummy translator should have been called for both files
    assert len(dummy_translator.calls) == 2
    called_inputs = {call[0].name for call in dummy_translator.calls}
    assert called_inputs == {"a.docx", "b.docx"}

    # language arguments propagated correctly
    for _, _, src, tgt in dummy_translator.calls:
        assert src == "EN"
        assert tgt == "JA"


def test_translate_dir_recursive(tmp_path: Path, dummy_translator: DummyTranslator) -> None:
    """
    Ensure --recursive finds .docx files in subdirectories.
    """
    in_dir = tmp_path / "in_docs"
    sub_dir = in_dir / "nested"
    out_dir = tmp_path / "out_docs"
    sub_dir.mkdir(parents=True)

    (in_dir / "root.docx").write_bytes(b"root")
    (sub_dir / "nested.docx").write_bytes(b"nested")

    exit_code = cli_mod.main(
        [
            "translate-dir",
            "-s",
            "EN",
            "-t",
            "JA",
            "-i",
            str(in_dir),
            "-o",
            str(out_dir),
            "--recursive",
        ]
    )

    assert exit_code == 0

    # Both root and nested documents should be translated
    assert (out_dir / "root.ja.docx").is_file()
    assert (out_dir / "nested.ja.docx").is_file()

    called_inputs = {call[0].name for call in dummy_translator.calls}
    assert called_inputs == {"root.docx", "nested.docx"}


def test_translate_dir_overwrite_flag(tmp_path: Path, dummy_translator: DummyTranslator) -> None:
    """
    Check that existing outputs are skipped unless --overwrite is given.
    """
    in_dir = tmp_path / "in_docs"
    out_dir = tmp_path / "out_docs"
    in_dir.mkdir()
    out_dir.mkdir()

    src_file = in_dir / "foo.docx"
    src_file.write_bytes(b"original")

    # Pre-create an output file
    out_file = out_dir / "foo.ja.docx"
    out_file.write_bytes(b"old")

    # 1) Without --overwrite: should SKIP
    exit_code = cli_mod.main(
        [
            "translate-dir",
            "-s",
            "EN",
            "-t",
            "JA",
            "-i",
            str(in_dir),
            "-o",
            str(out_dir),
        ]
    )

    assert exit_code == 0
    # DummyTranslator should not be called
    assert len(dummy_translator.calls) == 0
    assert out_file.read_bytes() == b"old"

    # 2) With --overwrite: should call translator and replace content
    dummy_translator.calls.clear()
    exit_code = cli_mod.main(
        [
            "translate-dir",
            "-s",
            "EN",
            "-t",
            "JA",
            "-i",
            str(in_dir),
            "-o",
            str(out_dir),
            "--overwrite",
        ]
    )

    assert exit_code == 0
    assert len(dummy_translator.calls) == 1
    # after "translation" we copied input -> output
    assert out_file.read_bytes() == b"original"


def test_translate_dir_missing_input_dir_returns_nonzero(tmp_path):
    """
    If the input directory does not exist, the CLI should fail
    with a non-zero exit code.

    Adjust the expected behavior/message if your design differs.
    """
    missing_dir = tmp_path / "no_such_dir"  # note: not created
    out_dir = tmp_path / "out_docs"

    exit_code = cli_mod.main(
        [
            "translate-dir",
            "-s",
            "EN",
            "-t",
            "JA",
            "-i",
            str(missing_dir),
            "-o",
            str(out_dir),
        ]
    )

    # We expect failure, so any non-zero is OK.
    assert exit_code != 0
    # And the CLI should not create the output directory on failure.
    assert not out_dir.exists()
