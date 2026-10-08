import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_pyproject_defines_ruff_line_length_140():
    data = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert data["tool"]["ruff"]["line-length"] == 140


def test_ruff_show_settings_reports_line_length_140():
    target = next(REPO_ROOT.glob("src/**/*.py"))
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "--show-settings", str(target)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    output = result.stdout
    assert "formatter.line_width = 140" in output
    assert "linter.line_length = 140" in output


def test_ruff_format_check_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0


def test_ruff_lint_check_exits_zero():
    result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", "."],
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0
