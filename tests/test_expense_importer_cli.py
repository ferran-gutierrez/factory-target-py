"""Console script import-expenses (REQ-11)."""

import subprocess
import sys
from decimal import Decimal
from importlib.metadata import entry_points
from pathlib import Path

import pytest

from factory_target_py import parse_expense_csv

SAMPLE_CSV = (
    "date,category,description,amount\n"
    "2024-05-01,Food,Lunch,10.00\n"
    "bad,Food,,1.00\n"
    "2024-05-02,Travel,Bus,5.00\n"
)


def _import_expenses_executable() -> Path:
    script = Path(sys.executable).resolve().parent / "import-expenses"
    if script.is_file():
        return script
    pytest.fail("import-expenses console script is not installed")


def test_import_expenses_entry_point_registered():
    """REQ-11: setuptools registers the import-expenses console script."""
    names = {ep.name for ep in entry_points(group="console_scripts")}
    assert "import-expenses" in names


def test_cli_reads_file_path_and_prints_human_readable_summary(tmp_path):
    """REQ-11: file path argument; stdout includes totals and errors; exit 0."""
    csv_file = tmp_path / "expenses.csv"
    csv_file.write_text(SAMPLE_CSV, encoding="utf-8")

    completed = subprocess.run(
        [str(_import_expenses_executable()), str(csv_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    out = completed.stdout
    assert "Food" in out
    assert "Travel" in out
    assert "2024-05" in out
    assert "10" in out or "10.00" in out
    assert "5" in out or "5.00" in out
    assert "2" in out  # error line number from invalid row
    assert completed.stderr == ""


def test_cli_reads_stdin_when_no_file_argument():
    """REQ-11: reads CSV text from standard input when path omitted."""
    completed = subprocess.run(
        [str(_import_expenses_executable())],
        input=SAMPLE_CSV,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    out = completed.stdout.lower()
    assert "food" in out
    assert "travel" in out
    assert "2024-05" in out
    assert "error" in out or "line" in out


def test_cli_uses_parse_expense_csv_for_totals():
    """REQ-11: CLI output reflects parse_expense_csv aggregates."""
    parsed = parse_expense_csv(SAMPLE_CSV)
    assert parsed.totals_by_category["Food"] == Decimal("10.00")
    assert parsed.totals_by_month["2024-05"] == Decimal("15.00")

    completed = subprocess.run(
        [str(_import_expenses_executable())],
        input=SAMPLE_CSV,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0
    food_total = str(parsed.totals_by_category["Food"]).rstrip("0").rstrip(".")
    stdout_normalized = completed.stdout.replace(",", "")
    assert food_total in stdout_normalized or "10" in completed.stdout
