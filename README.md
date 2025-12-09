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

## 🧰 Example Makefile for end users

If you prefer a simple `make` interface in your **own project** (not for developing this library itself), you can use a wrapper Makefile like the one below.  
Adjust the `VENV` path to your virtual environment, save this as `Makefile` (or `Makefile_sample.mk`) in your project root, and run `make help` to see the available targets.

```make
# Define variables
VENV   := /path/to/venv
BIN    = $(VENV)/bin
PYTHON = $(BIN)/python

.DEFAULT_GOAL := help

.PHONY: help ende deen ende-pro deen-pro

help: ## Show this help message
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@printf "  \033[36m%-15s\033[0m %s\n" "help" "Show this help message"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| grep -v '^help:' \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'


# ----------------------------------------------
# English <-> German Using FREE endpoint
# ----------------------------------------------
ende: ## Batch translate: in_docs -> out_docs, EN → DE
	$(PYTHON) -m docx_translator.cli \
		translate-dir \
		-s EN -t DE \
		-i in_docs -o out_docs \

deen: ## Batch translate: in_docs -> out_docs, DE → EN
	$(PYTHON) -m docx_translator.cli \
		translate-dir \
		-s DE -t EN \
		-i in_docs -o out_docs \

# ----------------------------------------------
# English <-> German Using PRO endpoint
# ----------------------------------------------
ende-pro: ## Batch translate: in_docs -> out_docs, EN → DE
	$(PYTHON) -m docx_translator.cli \
		translate-dir \
		-s EN -t DE \
		-i in_docs -o out_docs \
		--pro

deen-pro: ## Batch translate: in_docs -> out_docs, DE → EN
	$(PYTHON) -m docx_translator.cli \
		translate-dir \
		-s DE -t EN \
		-i in_docs -o out_docs \
		--pro
```

This sample Makefile is **not** installed by the package; it is only provided here as a reference for end users who like a `make`-based workflow.
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
