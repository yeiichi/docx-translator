from __future__ import annotations

from importlib import import_module

from docx_translator.core import translator as tr


def test_deepl_engine_module_is_importable() -> None:
    """
    Smoke test: DeepL engine module can be imported.

    This ensures the package layout and module paths are correct.
    """
    mod = import_module("docx_translator.engines.deepl_engine.engine")
    # The translator module imports DeepLEngine from here, so the symbol
    # should be defined at module level.
    assert hasattr(mod, "DeepLEngine")


def test_docx_translator_uses_deepl_engine_by_default(monkeypatch) -> None:
    """
    When no engine is passed, DocxTranslator should construct DeepLEngine().

    We avoid constructing the *real* DeepLEngine by monkeypatching the
    symbol that translator.py uses, and verify DocxTranslator picks it up.
    """
    created_instances = []

    class DummyEngine:
        def __init__(self) -> None:
            created_instances.append(self)

        def translate_segments(self, segments, source_lang, target_lang):
            # trivial "echo" for interface compatibility
            return list(segments)

    # Patch the DeepLEngine symbol that translator.DocxTranslator uses
    monkeypatch.setattr(tr, "DeepLEngine", DummyEngine)

    docx_translator = tr.DocxTranslator()  # no engine passed

    # It should have used our DummyEngine instead of any real engine
    assert isinstance(docx_translator.engine, DummyEngine)
    assert created_instances  # at least one instance created
