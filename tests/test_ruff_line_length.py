"""Ruff line length 140 configuration (REQ-1 through REQ-5, py-20261008-6sz1)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUFF_TOML = ROOT / "ruff.toml"
SRC_RUFF_TOML = ROOT / "src" / "ruff.toml"
TESTS_DIR = Path(__file__).resolve().parent
TESTS_RUFF_TOML = TESTS_DIR / "ruff.toml"
RUFF_LINE_LENGTH_WORK = TESTS_DIR / "ruff_line_length_work"


def _one_line_assignment(length: int) -> str:
    prefix = 'X = "'
    suffix = '"'
    padding = length - len(prefix) - len(suffix)
    assert padding >= 0
    line = prefix + ("#" * padding) + suffix
    assert len(line) == length
    return line + "\n"


def _run_ruff(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruff", *args],
        cwd=cwd or ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_REQ_1_ruff_toml_sets_line_length_140_and_preserves_other_keys():
    root = tomllib.loads(RUFF_TOML.read_text(encoding="utf-8"))
    assert root["line-length"] == 100
    assert root["target-version"] == "py312"
    assert root["src"] == ["src", "tests"]
    assert root["lint"]["select"] == ["E", "F", "I", "B", "UP"]
    for path in (SRC_RUFF_TOML, TESTS_RUFF_TOML):
        data = tomllib.loads(path.read_text(encoding="utf-8"))
        assert data["line-length"] == 140
        assert data["extend"] == "../ruff.toml"


def test_REQ_2_ruff_show_settings_reports_line_length_140():
    target = ROOT / "src" / "factory_target_py" / "__init__.py"
    result = _run_ruff("check", "--show-settings", str(target))
    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert "linter.line_length = 140" in output
    assert "formatter.line_width = 140" in output


def test_REQ_3_ruff_e501_boundary_at_139_and_141_under_tests():
    RUFF_LINE_LENGTH_WORK.mkdir(exist_ok=True)
    path_139 = RUFF_LINE_LENGTH_WORK / "line_139.py"
    path_141 = RUFF_LINE_LENGTH_WORK / "line_141.py"
    try:
        path_139.write_text(_one_line_assignment(139), encoding="utf-8")
        path_141.write_text(_one_line_assignment(141), encoding="utf-8")

        ok_result = _run_ruff("check", str(path_139))
        assert ok_result.returncode == 0, ok_result.stdout + ok_result.stderr
        assert "E501" not in ok_result.stdout + ok_result.stderr

        long_result = _run_ruff("check", str(path_141))
        combined = long_result.stdout + long_result.stderr
        assert "E501" in combined
    finally:
        shutil.rmtree(RUFF_LINE_LENGTH_WORK, ignore_errors=True)


def test_REQ_4_ruff_format_check_exits_zero_from_repository_root():
    result = _run_ruff("format", "--check", ".")
    assert result.returncode == 0, result.stdout + result.stderr


def test_REQ_5_ruff_check_exits_zero_from_repository_root():
    result = _run_ruff("check", ".")
    assert result.returncode == 0, result.stdout + result.stderr
