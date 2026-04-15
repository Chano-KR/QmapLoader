from __future__ import annotations

import os
import sys
import threading
import time
import webbrowser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

for stream in (sys.stdout, sys.stderr):
    try:
        stream.reconfigure(encoding="utf-8")
    except Exception:
        pass

import uvicorn  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.utils.port import choose_port  # noqa: E402


def _open_browser(url: str, delay: float = 1.5) -> None:
    time.sleep(delay)
    try:
        webbrowser.open(url)
    except Exception:
        pass


def main() -> int:
    settings = get_settings()
    try:
        port = choose_port(settings.primary_port, settings.fallback_port)
    except RuntimeError as exc:
        print(f"[오류] {exc}")
        print("다른 프로그램이 포트를 사용 중입니다. 해당 프로그램을 종료한 뒤 다시 시도해 주세요.")
        input("Enter 키를 누르면 종료합니다...")
        return 1

    url = f"http://127.0.0.1:{port}/"
    print("=" * 52)
    print(" QmapLoader 실행 중")
    print(f"  주소: {url}")
    print(f"  결과 폴더: {settings.resolved_output_dir()}")
    print("  종료하려면 이 창에서 Ctrl+C 를 누르세요.")
    print("=" * 52)

    if os.environ.get("QMAPLOADER_NO_BROWSER") != "1":
        threading.Thread(target=_open_browser, args=(url,), daemon=True).start()

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level=settings.log_level.lower(),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
