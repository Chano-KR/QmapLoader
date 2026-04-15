from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path


_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def sanitize_stem(stem: str) -> str:
    """Strip characters that Windows filesystems reject. Preserve Unicode letters."""
    cleaned = _UNSAFE_CHARS.sub("_", stem).strip().rstrip(".")
    return cleaned or "document"


def unique_output_path(output_dir: Path, stem: str, suffix: str = ".md") -> Path:
    """
    Return a non-colliding path in output_dir.

    sample.md -> sample.md (if free)
             -> sample_2026-04-15_143200.md (if sample.md exists)
             -> sample_2026-04-15_143200_2.md (if the timestamped name also exists)
    """
    safe_stem = sanitize_stem(stem)
    candidate = output_dir / f"{safe_stem}{suffix}"
    if not candidate.exists():
        return candidate

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    candidate = output_dir / f"{safe_stem}_{stamp}{suffix}"
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = output_dir / f"{safe_stem}_{stamp}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
