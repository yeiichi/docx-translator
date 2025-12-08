# docx-translator-smith

[![PyPI version](https://img.shields.io/pypi/v/docx-translator-smith.svg)](https://pypi.org/project/docx-translator-smith/)
![Python versions](https://img.shields.io/pypi/pyversions/docx-translator-smith.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Status](https://img.shields.io/badge/status-Alpha-orange.svg)

A lightweight, developer-friendly DOCX translation tool powered by the DeepL API.  
Provides both a **Python library** and **CLI tools** for batch-translating Microsoft Word (`.docx`) files while preserving structure.

---

## ✨ Features

- Translate DOCX documents using the DeepL API  
- Preserve document structure (runs, paragraphs, tables)  
- Automatic deduplication for translation memory efficiency  
- Batch translation (entire folders)  
- Benchmark mode to measure throughput and latency  
- CLI commands suitable for automation

---

## 📦 Installation

```bash
pip install docx-translator-smith
```

Requires **Python 3.11+**.

---

## 🚀 Quick Start (CLI)

Translate an entire directory:

```bash
docx-translator     translate-dir     -s EN     -t JA     -i in_docs     -o out_docs
```

Benchmark translation performance:

```bash
docx-translator-bench     --src EN     --tgt JA     --input-dir in_docs     --output-dir out_docs     -v
```

---

## 🐍 Quick Start (Python)

```python
from docx_translator.core.translator import translate_docx

src_path = "example.docx"
dst_path = "example.ja.docx"

translate_docx(src_path, dst_path, src_lang="EN", tgt_lang="JA")
```

---

## 🔑 Requirements

- DeepL API key  
- Python 3.11 or later  
- `python-docx`, `requests`

Export your DeepL API key:

```bash
export DEEPL_API_KEY="your-key"
```

---

## 🛠 Development

```bash
git clone https://github.com/yeiichi/docx-translator
cd docx-translator
make venv
make install
make test
```

Build & publish:

```bash
make build
make dist-check
make publish
```

---

## 📄 License

MIT License © 2025 Eiichi Yamamoto  
See `LICENSE` for full text.

---

## 👤 Author

**Eiichi Yamamoto**

---

## 📌 Project Status

This is an **Alpha** release — stable for CLI use, but internal APIs may evolve.

---

## 🔗 Links

- PyPI: <https://pypi.org/project/docx-translator-smith/>
- Source Code: <https://github.com/yeiichi/docx-translator/>
- Issues: <https://github.com/yeiichi/docx-translator/issues>
