"""Silent printing via Chrome headless -> PDF -> lpr."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

PDF_DIR = Path("/tmp/hatena_pdf")
PDF_DIR.mkdir(exist_ok=True)


def generate_pdf(result_id: str, frontend_base: str = "http://localhost:3000") -> Path:
    """結果ページをChrome headlessでPDF化して保存する。"""
    chrome = _find_chrome()
    if chrome is None:
        raise RuntimeError("Google Chrome / Chromium が見つかりません。")

    pdf_path = PDF_DIR / f"{result_id}.pdf"
    url = f"{frontend_base}/result/{result_id}"

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
            "--paper-width=5.83",
            "--paper-height=8.27",
            "--window-size=559,794",
            "--virtual-time-budget=5000",
            url,
        ],
        check=True,
        timeout=30,
        capture_output=True,
    )
    return pdf_path


def generate_pdf_background(result_id: str, frontend_base: str = "http://localhost:3000") -> None:
    """バックグラウンドでPDFを事前生成する。"""
    def _run():
        try:
            generate_pdf(result_id, frontend_base)
        except Exception as e:
            print(f"[PDF事前生成エラー] {result_id}: {e}")
    threading.Thread(target=_run, daemon=True).start()

# station番号 → プリンター名の対応表
# .env.production の PRINTER_1, PRINTER_2 を参照
STATION_PRINTER_MAP: dict[int, str] = {
    1: os.environ.get("PRINTER_1", ""),
    2: os.environ.get("PRINTER_2", ""),
    3: os.environ.get("PRINTER_3", ""),
}


def _find_chrome() -> str | None:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    return shutil.which("google-chrome") or shutil.which("chromium")


def print_result(
    result_id: str,
    frontend_base: str = "http://localhost:3000",
    station: int = 1,
) -> None:
    """Render the result page with Chrome headless and send to the printer
    assigned to the given station number.

    Raises RuntimeError if Chrome is not found or printing fails.
    """
    chrome = _find_chrome()
    if chrome is None:
        raise RuntimeError(
            "Google Chrome / Chromium が見つかりません。"
            "/Applications にインストールされているか確認してください。"
        )

    # station番号からプリンター名を取得
    printer_name = STATION_PRINTER_MAP.get(station, "")
    if not printer_name:
        raise RuntimeError(
            f"station={station} に対応するプリンターが設定されていません。"
            ".env.production の PRINTER_1 / PRINTER_2 を確認してください。"
        )

    # 事前生成済みPDFがあれば使う、なければ生成する
    pdf_path = PDF_DIR / f"{result_id}.pdf"
    if not pdf_path.exists():
        pdf_path = generate_pdf(result_id, frontend_base)

    try:
        subprocess.run(
            ["lpr", "-P", printer_name, "-o", "media=A5", "-o", "CNDuplex=None", "-o", "Duplex=None", "-o", "sides=one-sided", str(pdf_path)],
            check=True,
            timeout=10,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"印刷処理に失敗しました: {e}") from e
    except subprocess.TimeoutExpired as e:
        raise RuntimeError("印刷処理がタイムアウトしました") from e
    finally:
        # 印刷完了後にPDFを削除
        try:
            pdf_path.unlink(missing_ok=True)
        except OSError:
            pass
