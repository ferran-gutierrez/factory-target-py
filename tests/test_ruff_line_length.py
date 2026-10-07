import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUFF_CONFIG_FRAGMENT = ROOT / "specs" / "py-20261007-fdc6-ruff-config.toml"


def _pyproject_ruff() -> dict:
    data = tomllib.loads(RUFF_CONFIG_FRAGMENT.read_text(encoding="utf-8"))
    return data["tool"]["ruff"]


def test_REQ_1_pyproject_ruff_line_length_and_migrated_settings():
    ruff = _pyproject_ruff()
    assert ruff["line-length"] == 140
    assert ruff["target-version"] == "py312"
    assert ruff["src"] == ["src", "tests"]
    lint = ruff["lint"]
    assert lint["select"] == ["E", "F", "I", "B", "UP"]


def test_REQ_2_ruff_check_show_settings_reports_line_length_140():
    assert _pyproject_ruff()["line-length"] == 140
    for target in ("src", "tests"):
        result = subprocess.run(
            [sys.executable, "-m", "ruff", "check", "--show-settings", target],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        match = re.search(r"^linter\.line_length\s*=\s*(\d+)", result.stdout, re.MULTILINE)
        assert match is not None
        assert int(match.group(1)) == 140


def test_REQ_3_ruff_format_check_exits_zero_on_repository_tree():
    subprocess.run(
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        cwd=ROOT,
        check=True,
    )


def test_REQ_4_single_line_130_chars_accepted_under_src():
    prefix = "_ = "
    payload_len = 130 - len(prefix) - 2
    source = f'{prefix}"{"x" * payload_len}"\n'
    assert len(source.rstrip("\n")) == 130
    path = ROOT / "src" / "factory_target_py" / "_req4_line_length_probe.py"
    path.write_text(source, encoding="utf-8")
    try:
        subprocess.run(
            [sys.executable, "-m", "ruff", "format", "--check", str(path)],
            cwd=ROOT,
            check=True,
        )
    finally:
        path.unlink(missing_ok=True)
