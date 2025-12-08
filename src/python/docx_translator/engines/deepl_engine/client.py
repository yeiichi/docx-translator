#!/usr/bin/env python3
"""
Thin DeepL HTTP client wrapper for docx-translator.

This module is intentionally small and focused:

- Read API key / URL from arguments or environment.
- Send a single HTTP request to DeepL's v2/translate endpoint.
- Provide simple retry logic with exponential backoff.
- Return translated texts in the same order as the input list.

High-level logic such as deduplication and DOCX layout mapping is handled
in higher layers (for example, in docx_translator.core.translator).
"""

from __future__ import annotations

import logging
import os
import time
from typing import List, Sequence

import requests

logger = logging.getLogger(__name__)

# Default to the Free endpoint; callers (or the CLI) can override via:
#   - api_url argument, or
#   - DEEPL_API_URL environment variable
DEFAULT_DEEPL_API_URL = "https://api-free.deepl.com/v2/translate"


class DeepLClient:
    """
    Synchronous HTTP client for DeepL's v2/translate API.

    Parameters
    ----------
    api_key:
        DeepL authentication key. If omitted, DEEPL_API_KEY from the
        environment will be used. If neither is available, a RuntimeError
        is raised.
    api_url:
        Full DeepL API URL for the translate endpoint. If omitted, the
        client will look for DEEPL_API_URL in the environment and fall
        back to DEFAULT_DEEPL_API_URL.
    timeout_seconds:
        Per-request timeout in seconds.
    max_attempts:
        Maximum number of attempts for a call (including the first
        attempt). Transient errors (network issues, HTTP 429/5xx) are
        retried with backoff until this limit is reached.
    backoff_seconds:
        Base backoff in seconds. The effective backoff for attempt n is
        backoff_seconds * n.
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_url: str | None = None,
        timeout_seconds: float = 20.0,
        max_attempts: int = 3,
        backoff_seconds: float = 1.0,
    ) -> None:
        self.api_key = api_key or os.getenv("DEEPL_API_KEY")
        if not self.api_key:
            raise RuntimeError(
                "DEEPL_API_KEY is not set and no api_key was passed to DeepLClient."
            )

        self.api_url = api_url or os.getenv("DEEPL_API_URL") or DEFAULT_DEEPL_API_URL
        self.timeout_seconds = timeout_seconds
        self.max_attempts = max_attempts
        self.backoff_seconds = backoff_seconds

        self._session = requests.Session()
        # A small, explicit UA helps debugging and log analysis.
        self._session.headers.update({"User-Agent": "docx-translator/DeepLClient"})

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def translate_texts(
        self,
        texts: Sequence[str],
        source_lang: str,
        target_lang: str,
        preserve_formatting: bool = True,
    ) -> List[str]:
        """
        Translate a list of texts in a single HTTP call.

        Parameters
        ----------
        texts:
            Sequence of input strings. Order is preserved in the output.
        source_lang:
            Source language code (for example "EN").
        target_lang:
            Target language code (for example "JA").
        preserve_formatting:
            If True, DeepL's preserve_formatting=1 option is used so that
            hard line breaks and simple structure are kept.

        Returns
        -------
        list of str
            Translated texts in the same order as texts.
        """
        if not texts:
            return []

        # DeepL expects ISO-style codes in uppercase.
        source_lang = source_lang.upper()
        target_lang = target_lang.upper()

        expected_len = len(texts)

        # Build form-encoded payload explicitly to keep ordering clear.
        data: list[tuple[str, str]] = [
            ("auth_key", self.api_key),
            ("source_lang", source_lang),
            ("target_lang", target_lang),
            ("preserve_formatting", "1" if preserve_formatting else "0"),
        ]
        for t in texts:
            data.append(("text", t))

        last_error: Exception | None = None

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.debug(
                    "DeepL request: %d text item(s), attempt %d/%d",
                    expected_len,
                    attempt,
                    self.max_attempts,
                )

                resp = self._session.post(
                    self.api_url,
                    data=data,
                    timeout=self.timeout_seconds,
                )

                # Retry on typical transient errors / rate limiting.
                if resp.status_code in {429, 500, 502, 503, 504}:
                    last_error = RuntimeError(
                        f"DeepL temporary error: HTTP {resp.status_code} - "
                        f"{resp.text[:500]}"
                    )
                    logger.warning(
                        "DeepL temporary error (will retry if attempts remain): %s",
                        last_error,
                    )
                elif not resp.ok:
                    # Non-retryable HTTP errors: fail fast.
                    raise RuntimeError(
                        f"DeepL API error: HTTP {resp.status_code} - "
                        f"{resp.text[:500]}"
                    )
                else:
                    payload = resp.json()
                    translations = payload.get("translations") or []
                    texts_out = [t.get("text", "") for t in translations]

                    if len(texts_out) != expected_len:
                        raise RuntimeError(
                            "DeepL response length mismatch: expected "
                            f"{expected_len}, got {len(texts_out)}"
                        )

                    return texts_out

            except (requests.RequestException, ValueError) as exc:
                # Network error or JSON decode error.
                last_error = exc
                logger.warning(
                    "DeepL request error (will retry if attempts remain): %s", exc
                )

            # Backoff before the next attempt, unless this was the last one.
            if attempt < self.max_attempts:
                backoff = self.backoff_seconds * attempt
                logger.debug("Sleeping %.2f seconds before retry", backoff)
                time.sleep(backoff)

        # Out of attempts.
        raise RuntimeError(
            f"DeepL API request failed after {self.max_attempts} attempts"
            + (f": last error: {last_error}" if last_error else "")
        )
