"""CLI --format flag for python -m factory_target_py.expenses (REQ-1 through REQ-8)."""

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


def test_REQ_2_explicit_json_matches_omitted_format(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,8.00\n"
        "2024-05-02,Travel,Flight,4.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\n", encoding="utf-8")

    omitted = _run_expenses_module(str(csv_path), "--budgets", str(budgets_path))
    explicit = _run_expenses_module(
        str(csv_path),
        "--format",
        "json",
        "--budgets",
        str(budgets_path),
    )

    assert omitted.returncode == 0, omitted.stderr
    assert explicit.returncode == 0, explicit.stderr
    assert json.loads(explicit.stdout) == json.loads(omitted.stdout)


def test_REQ_3_csv_prints_category_totals_sorted_by_plain_string(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Travel,Flight,4.00\n"
        "2024-05-02,Food,Lunch,8.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path), "--format", "csv")

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "category,total",
        "Food,8.00",
        "Travel,4.00",
    ]


def test_REQ_4_csv_with_month_reflects_filtered_category_totals(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-03-15,Food,March,5.00\n"
        "2024-04-01,Food,April,7.00\n"
        "2024-04-02,Travel,April trip,3.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(
        str(csv_path),
        "--format",
        "csv",
        "--month",
        "2024-04",
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "category,total",
        "Food,7.00",
        "Travel,3.00",
    ]


def test_REQ_5_csv_reports_import_errors_on_stderr_without_json(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-03-15,Food,Ok,5.00\n"
        "2024-04-01,,Bad category,7.00\n"
        "2024-05-01,Travel,,9.00\n",
        encoding="utf-8",
    )

    json_result = _run_expenses_module(str(csv_path))
    csv_result = _run_expenses_module(str(csv_path), "--format", "csv")

    assert csv_result.returncode == 0, csv_result.stderr
    assert json_result.returncode == 0, json_result.stderr
    json_errors = json.loads(json_result.stdout)["errors"]
    assert csv_result.stderr.splitlines() == [
        f"line {entry['line']}: {entry['reason']}" for entry in json_errors
    ]
    assert csv_result.stdout.splitlines() == [
        "category,total",
        "Food,5.00",
    ]
    assert "{" not in csv_result.stdout


def test_REQ_6_csv_sorts_categories_by_plain_string_not_casefold(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,apple,Fruit,1.00\n"
        "2024-05-02,Banana,Fruit,2.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path), "--format", "csv")

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == [
        "category,total",
        "Banana,2.00",
        "apple,1.00",
    ]


def test_REQ_7_invalid_format_writes_usage_and_exits_without_reading(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )
    for args in (
        (str(csv_path), "--format", "xml"),
        (str(csv_path), "--format", "JSON"),
        (str(csv_path), "--format"),
    ):
        result = _run_expenses_module(*args)
        assert result.returncode == 1, args
        assert "usage" in result.stderr.lower(), args
        assert result.stdout.strip() == "", args


def test_REQ_8_readable_file_exits_zero_for_csv_and_json_with_invalid_rows(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-05-01,,Snack,3.00\n",
        encoding="utf-8",
    )

    json_result = _run_expenses_module(str(csv_path))
    csv_result = _run_expenses_module(str(csv_path), "--format", "csv")

    assert json_result.returncode == 0
    assert csv_result.returncode == 0


def test_REQ_8_unreadable_expense_and_budget_errors_produce_no_success_stdout_in_csv(
    tmp_path: Path,
):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )
    missing_expenses = tmp_path / "missing-expenses.csv"
    missing_budgets = tmp_path / "missing-budgets.csv"
    bad_budgets = tmp_path / "budgets.csv"
    bad_budgets.write_text("category,limit\nFood,0\n", encoding="utf-8")

    unreadable_expense = _run_expenses_module(
        str(missing_expenses),
        "--format",
        "csv",
    )
    assert unreadable_expense.returncode != 0
    assert unreadable_expense.stdout.strip() == ""

    unreadable_budget = _run_expenses_module(
        str(expenses_path),
        "--format",
        "csv",
        "--budgets",
        str(missing_budgets),
    )
    assert unreadable_budget.returncode != 0
    assert unreadable_budget.stdout.strip() == ""

    invalid_budget = _run_expenses_module(
        str(expenses_path),
        "--format",
        "csv",
        "--budgets",
        str(bad_budgets),
    )
    assert invalid_budget.returncode != 0
    assert invalid_budget.stdout.strip() == ""

    dup_path = tmp_path / "dup.csv"
    dup_path.write_text("category,limit\nFood,10.00\nfood,20.00\n", encoding="utf-8")
    duplicate_budget = _run_expenses_module(
        str(expenses_path),
        "--format",
        "csv",
        "--budgets",
        str(dup_path),
    )
    assert duplicate_budget.returncode != 0
    assert duplicate_budget.stdout.strip() == ""


def test_REQ_9_format_month_and_budgets_flags_may_appear_in_any_order(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,May,12.00\n2024-06-01,Food,June,20.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\n", encoding="utf-8")

    order_a = _run_expenses_module(
        str(expenses_path),
        "--format",
        "csv",
        "--month",
        "2024-05",
        "--budgets",
        str(budgets_path),
    )
    order_b = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--budgets",
        str(budgets_path),
        "--format",
        "csv",
    )

    assert order_a.returncode == 0, order_a.stderr
    assert order_b.returncode == 0, order_b.stderr
    assert order_a.stdout == order_b.stdout
    assert order_a.stderr == order_b.stderr

    json_a = _run_expenses_module(
        str(expenses_path),
        "--format",
        "json",
        "--month",
        "2024-05",
    )
    json_b = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--format",
        "json",
    )
    assert json_a.returncode == 0, json_a.stderr
    assert json_b.returncode == 0, json_b.stderr
    assert json_a.stdout == json_b.stdout


def test_duplicate_format_flag_writes_usage_and_exits_nonzero(tmp_path: Path):
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

    assert result.returncode != 0
    assert "usage" in result.stderr.lower()
    assert result.stdout.strip() == ""
