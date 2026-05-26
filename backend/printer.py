"""Silent printing via Chrome headless -> PDF -> lpr."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path


def _find_chrome() -> str | None:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return shutil.which("google-chrome") or shutil.which("chromium")


def print_result(result_id: str, frontend_base: str = "http://localhost:3000") -> None:
    """Render the result page with Chrome headless and send to default printer.

    Raises RuntimeError if Chrome is not found or printing fails.
    """
    chrome = _find_chrome()
    if chrome is None:
        raise RuntimeError(
            "Google Chrome / Chromium が見つかりません。"
            "/Applications にインストールされているか確認してください。"
        )

    url = f"{frontend_base}/result/{result_id}"

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        pdf_path = f.name

    try:
        subprocess.run(
            [
                chrome,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--print-to-pdf={pdf_path}",
                "--print-to-pdf-no-header",
                "--no-margins",
                "--virtual-time-budget=5000",
                url,
            ],
            check=True,
            timeout=30,
            capture_output=True,
        )

        subprocess.run(["lpr", "-P", "ENTAKUc__c_5c__c_9", "-o", "CNDuplex=None", pdf_path], check=True, timeout=10)

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"印刷処理に失敗しました: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("印刷処理がタイムアウトしました") from e
    finally:
        try:
            os.unlink(pdf_path)
        except OSError:
            pass
