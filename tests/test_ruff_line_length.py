"""Verification tests for ruff line-length 140 (py-20261007-s98z)."""

from __future__ import annotations

import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUFF_TOML = REPO_ROOT / "ruff.toml"
TESTS_RUFF_TOML = REPO_ROOT / "tests" / "ruff.toml"

EXPECTED_TARGET_VERSION = "py312"
EXPECTED_SRC = ["src", "tests"]
EXPECTED_LINT_SELECT = ["E", "F", "I", "B", "UP"]


def _run_ruff(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruff", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_REQ_1_ruff_toml_line_length_and_unchanged_fields() -> None:
    with RUFF_TOML.open("rb") as handle:
        ruff_config = tomllib.load(handle)

    assert ruff_config["line-length"] == 100
    assert isinstance(ruff_config["line-length"], int)
    assert ruff_config["target-version"] == EXPECTED_TARGET_VERSION
    assert ruff_config["src"] == EXPECTED_SRC
    assert ruff_config["lint"]["select"] == EXPECTED_LINT_SELECT

    with TESTS_RUFF_TOML.open("rb") as handle:
        tests_ruff_config = tomllib.load(handle)

    assert tests_ruff_config["line-length"] == 140
    assert isinstance(tests_ruff_config["line-length"], int)


def test_REQ_2_format_leaves_130_char_string_assignment_on_one_line() -> None:
    literal = "a" * 130
    source_line = f'x = "{literal}"'
    assert len(literal) == 130
    module_path = REPO_ROOT / "tests" / "_ruff_line_length_synthetic.py"
    module_path.write_text(f"{source_line}\n", encoding="utf-8")
    try:
        result = _run_ruff("format", str(module_path.relative_to(REPO_ROOT)))
        assert result.returncode == 0, result.stderr or result.stdout

        formatted = module_path.read_text(encoding="utf-8")
        physical_lines = [line for line in formatted.splitlines() if line.strip()]
        assert physical_lines == [source_line]
    finally:
        if module_path.exists():
            module_path.unlink()


def test_REQ_3_ruff_check_exits_zero_with_no_violations() -> None:
    result = _run_ruff("check", ".")
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Found" not in result.stdout


def test_REQ_4_ruff_format_check_exits_zero_for_src_and_tests() -> None:
    result = _run_ruff("format", "--check", ".")
    assert result.returncode == 0, result.stdout + result.stderr
    combined = result.stdout + result.stderr
    assert "would be reformatted" not in combined.lower()
