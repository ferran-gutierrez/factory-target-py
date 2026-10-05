"""CLI --format json|csv for python -m factory_target_py.expenses."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _run_expenses_module(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "factory_target_py.expenses", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_REQ_2_csv_stdout_category_totals_header_and_sorted_rows(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Travel,Flight,10.00\n"
        "2024-05-02,Food,Lunch,8.00\n"
        "2024-05-03,Food,Dinner,4.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path), "--format", "csv")

    assert result.returncode == 0, result.stderr
    lines = result.stdout.splitlines()
    assert lines == ["category,total", "Food,12.00", "Travel,10.00"]


def test_REQ_3_csv_invalid_rows_on_stderr_no_json_on_stdout(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Ok,5.00\n"
        "2024-04-01,,Bad,7.00\n"
        "2024-05-01,Travel,,9.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path), "--format", "csv")

    assert result.returncode == 0, result.stderr
    assert result.stderr.splitlines() == [
        "line 3: empty category",
        "line 4: empty description",
    ]
    assert result.stdout.splitlines() == ["category,total", "Food,5.00"]
    assert not result.stdout.strip().startswith("{")


def test_REQ_4_csv_sorts_categories_by_plain_string_not_casefold(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,apple,Fruit,1.00\n"
        "2024-05-02,Banana,Fruit,2.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path), "--format", "csv")

    assert result.returncode == 0, result.stderr
    data_lines = result.stdout.splitlines()[1:]
    assert data_lines == ["Banana,2.00", "apple,1.00"]


def test_REQ_5_invalid_format_writes_usage_and_exits_nonzero(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )

    missing_value = _run_expenses_module(str(csv_path), "--format")
    assert missing_value.returncode == 1
    assert "usage" in missing_value.stderr.lower()
    assert missing_value.stdout == ""

    bad_value = _run_expenses_module(str(csv_path), "--format", "xml")
    assert bad_value.returncode == 1
    assert "usage" in bad_value.stderr.lower()
    assert bad_value.stdout == ""


def test_REQ_6_format_month_and_budgets_flags_order_independent_for_csv(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-03-15,Food,March,5.00\n"
        "2024-04-01,Food,April,7.00\n",
        encoding="utf-8",
    )

    format_first = _run_expenses_module(
        str(csv_path),
        "--format",
        "csv",
        "--month",
        "2024-04",
    )
    month_first = _run_expenses_module(
        str(csv_path),
        "--month",
        "2024-04",
        "--format",
        "csv",
    )

    assert format_first.returncode == 0, format_first.stderr
    assert month_first.returncode == 0, month_first.stderr
    assert format_first.stdout == month_first.stdout
    assert format_first.stdout.splitlines() == ["category,total", "Food,7.00"]


def test_REQ_7_csv_month_filter_matches_json_category_totals(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-03-15,Food,March,5.00\n"
        "2024-04-01,Food,April,7.00\n",
        encoding="utf-8",
    )

    json_result = _run_expenses_module(str(csv_path), "--month", "2024-04")
    csv_result = _run_expenses_module(
        str(csv_path),
        "--format",
        "csv",
        "--month",
        "2024-04",
    )

    assert json_result.returncode == 0, json_result.stderr
    assert csv_result.returncode == 0, csv_result.stderr
    payload = json.loads(json_result.stdout)
    csv_lines = csv_result.stdout.splitlines()
    assert csv_lines[0] == "category,total"
    assert len(csv_lines) == 1 + len(payload["category_totals"])
    for line in csv_lines[1:]:
        category, total = line.split(",", 1)
        assert payload["category_totals"][category] == total


def test_REQ_8_duplicate_format_flag_writes_usage_and_exits_nonzero(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(
        str(csv_path),
        "--format",
        "csv",
        "--format",
        "json",
    )

    assert result.returncode == 1
    assert "usage" in result.stderr.lower()
    assert result.stdout == ""


def test_REQ_1_explicit_json_matches_default_output(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,8.00\n"
        "2024-05-02,Food,Dinner,4.00\n",
        encoding="utf-8",
    )

    default_result = _run_expenses_module(str(csv_path))
    json_result = _run_expenses_module(str(csv_path), "--format", "json")

    assert default_result.returncode == 0, default_result.stderr
    assert json_result.returncode == 0, json_result.stderr
    assert json.loads(default_result.stdout) == json.loads(json_result.stdout)


def test_csv_empty_categories_still_prints_header(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-03-15,Food,Ok,5.00\n2024-04-01,,Bad,7.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(
        str(csv_path),
        "--format",
        "csv",
        "--month",
        "2024-01",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["category,total"]
