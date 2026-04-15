from __future__ import annotations

from pathlib import Path

from app.utils.filenames import sanitize_stem, unique_output_path


def test_sanitize_stem_removes_windows_unsafe_chars():
    assert sanitize_stem('a<b>c:d"e/f\\g|h?i*j') == "a_b_c_d_e_f_g_h_i_j"


def test_sanitize_stem_preserves_unicode():
    assert sanitize_stem("수학_문제집") == "수학_문제집"


def test_sanitize_stem_falls_back_when_empty():
    assert sanitize_stem("   ") == "document"
    assert sanitize_stem("...") == "document"


def test_unique_output_path_returns_base_when_free(tmp_path: Path):
    result = unique_output_path(tmp_path, "sample")
    assert result == tmp_path / "sample.md"


def test_unique_output_path_adds_timestamp_on_collision(tmp_path: Path):
    (tmp_path / "sample.md").write_text("existing")
    result = unique_output_path(tmp_path, "sample")
    assert result.name.startswith("sample_")
    assert result.suffix == ".md"
    assert result != tmp_path / "sample.md"
