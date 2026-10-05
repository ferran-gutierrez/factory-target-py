"""CLI for python -m factory_target_py.expenses (REQ-11 through REQ-14)."""

from __future__ import annotations

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

from factory_target_py.expenses import money_to_json_string


def _run_expenses_module(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "factory_target_py.expenses", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_reads_file_and_prints_json_result(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,8.00\n"
        "2024-05-02,Food,Dinner,4.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {"category_totals", "month_totals", "errors"}
    assert payload["category_totals"] == {"Food": "12.00"}
    assert payload["month_totals"] == {"2024-05": "12.00"}
    assert payload["errors"] == []
    assert all(isinstance(value, str) for value in payload["category_totals"].values())
    assert all(isinstance(value, str) for value in payload["month_totals"].values())


def test_cli_json_error_objects_use_line_and_reason_keys(tmp_path: Path):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-05-01,,Snack,3.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert len(payload["errors"]) == 1
    assert set(payload["errors"][0].keys()) == {"line", "reason"}
    assert payload["errors"][0]["line"] == 2
    assert payload["errors"][0]["reason"] == "empty category"


def test_cli_wrong_argument_count_writes_usage_to_stderr_and_exits_nonzero():
    no_args = _run_expenses_module()
    assert no_args.returncode != 0
    assert "usage" in no_args.stderr.lower()

    too_many = _run_expenses_module("a.csv", "b.csv")
    assert too_many.returncode != 0
    assert "usage" in too_many.stderr.lower()


def test_cli_budgets_flag_without_path_writes_usage_to_stderr_and_exits_nonzero(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path), "--budgets")

    assert result.returncode != 0
    assert "usage" in result.stderr.lower()
    assert result.stdout.strip() == ""


def test_cli_with_budgets_prints_budget_alerts_in_json(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,8.00\n"
        "2024-05-02,Food,Dinner,4.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\n", encoding="utf-8")

    result = _run_expenses_module(str(expenses_path), "--budgets", str(budgets_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {
        "category_totals",
        "month_totals",
        "errors",
        "budget_alerts",
    }
    assert payload["category_totals"] == {"Food": "12.00"}
    assert payload["month_totals"] == {"2024-05": "12.00"}
    assert payload["errors"] == []
    assert payload["budget_alerts"] == [
        {
            "month": "2024-05",
            "category": "Food",
            "total": "12.00",
            "limit": "10.00",
            "amount_over": "2.00",
        }
    ]
    alert = payload["budget_alerts"][0]
    assert all(isinstance(alert[key], str) for key in ("total", "limit", "amount_over"))


def test_cli_unreadable_expense_file_exits_nonzero_with_traceback_on_stderr(tmp_path: Path):
    missing_expenses = tmp_path / "missing-expenses.csv"

    result = _run_expenses_module(str(missing_expenses))

    assert result.returncode != 0
    assert result.stderr.splitlines() == [str(missing_expenses)]
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == ""


def test_cli_unreadable_budgets_file_exits_nonzero_without_success_json(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )
    missing_budgets = tmp_path / "missing-budgets.csv"

    result = _run_expenses_module(
        str(expenses_path),
        "--budgets",
        str(missing_budgets),
    )

    assert result.returncode != 0
    assert result.stderr.splitlines() == [str(missing_budgets)]
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == ""


def test_REQ_3_cli_budget_alerts_json_order_matches_case_insensitive_category_sort(
    tmp_path: Path,
):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n"
        "2024-01-01,food,Lunch,15.00\n"
        "2024-01-02,Travel,Flight,15.00\n"
        "2024-02-01,Food,Meal,50.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text(
        "category,limit\nTravel,10.00\nfood,10.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(expenses_path), "--budgets", str(budgets_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [alert["category"] for alert in payload["budget_alerts"]] == [
        "food",
        "Travel",
        "food",
    ]
    assert [alert["month"] for alert in payload["budget_alerts"]] == [
        "2024-01",
        "2024-01",
        "2024-02",
    ]


def test_REQ_4_cli_unreadable_expense_file_one_stderr_line_no_traceback(tmp_path: Path):
    missing_expenses = tmp_path / "no-such-expenses.csv"

    result = _run_expenses_module(str(missing_expenses))

    assert result.returncode != 0
    assert result.stderr.splitlines() == [str(missing_expenses)]
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == ""


def test_REQ_5_cli_unreadable_budgets_file_one_stderr_line_no_traceback(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )
    missing_budgets = tmp_path / "no-such-budgets.csv"

    result = _run_expenses_module(
        str(expenses_path),
        "--budgets",
        str(missing_budgets),
    )

    assert result.returncode != 0
    assert result.stderr.splitlines() == [str(missing_budgets)]
    assert "Traceback" not in result.stderr
    assert result.stdout.strip() == ""


def test_REQ_6_cli_month_flag_unreadable_paths_and_invalid_budgets_stderr(tmp_path: Path):
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
        "--month",
        "2024-05",
        "--budgets",
        str(bad_budgets),
    )
    assert unreadable_expense.returncode != 0
    assert unreadable_expense.stderr.splitlines() == [str(missing_expenses)]
    assert "Traceback" not in unreadable_expense.stderr
    assert unreadable_expense.stdout.strip() == ""

    unreadable_budget = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--budgets",
        str(missing_budgets),
    )
    assert unreadable_budget.returncode != 0
    assert unreadable_budget.stderr.splitlines() == [str(missing_budgets)]
    assert "Traceback" not in unreadable_budget.stderr
    assert unreadable_budget.stdout.strip() == ""

    invalid_budget = _run_expenses_module(
        str(expenses_path),
        "--budgets",
        str(bad_budgets),
        "--month",
        "2024-05",
    )
    assert invalid_budget.returncode != 0
    assert invalid_budget.stderr.strip() == "invalid limit"
    assert invalid_budget.stdout.strip() == ""


def test_cli_prints_two_decimal_strings_for_fraction_category_total(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n2024-03-01,Food,A,0.10\n2024-03-02,Food,B,0.20\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,100.00\n", encoding="utf-8")

    result = _run_expenses_module(str(csv_path), "--budgets", str(budgets_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["category_totals"] == {"Food": "0.30"}
    assert payload["month_totals"] == {"2024-03": "0.30"}
    assert payload["budget_alerts"] == []


def test_cli_invalid_budgets_csv_exits_nonzero_without_success_json(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,0\n", encoding="utf-8")

    result = _run_expenses_module(str(expenses_path), "--budgets", str(budgets_path))

    assert result.returncode != 0
    assert result.stderr.strip() != ""
    assert result.stdout.strip() == ""


def _two_month_food_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-03-15,Food,March meal,5.00\n"
        "2024-04-01,Food,April meal,7.00\n",
        encoding="utf-8",
    )
    return csv_path


def test_REQ_1_month_json_field_present_only_when_flag_supplied(tmp_path: Path):
    csv_path = _two_month_food_csv(tmp_path)

    without_month = _run_expenses_module(str(csv_path))
    assert without_month.returncode == 0, without_month.stderr
    payload_no_flag = json.loads(without_month.stdout)
    assert "month" not in payload_no_flag

    with_month = _run_expenses_module(str(csv_path), "--month", "2024-04")
    assert with_month.returncode == 0, with_month.stderr
    payload_with_flag = json.loads(with_month.stdout)
    assert payload_with_flag["month"] == "2024-04"


def test_REQ_2_category_totals_filtered_to_selected_month(tmp_path: Path):
    csv_path = _two_month_food_csv(tmp_path)

    result = _run_expenses_module(str(csv_path), "--month", "2024-04")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["category_totals"] == {"Food": "7.00"}


def test_REQ_3_month_totals_include_only_requested_month(tmp_path: Path):
    csv_path = _two_month_food_csv(tmp_path)

    result = _run_expenses_module(str(csv_path), "--month", "2024-04")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["month_totals"] == {"2024-04": "7.00"}
    assert "2024-03" not in payload["month_totals"]


def test_REQ_4_empty_totals_when_no_rows_in_selected_month(tmp_path: Path):
    csv_path = _two_month_food_csv(tmp_path)
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,100.00\n", encoding="utf-8")

    result = _run_expenses_module(
        str(csv_path),
        "--month",
        "2024-01",
        "--budgets",
        str(budgets_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["month"] == "2024-01"
    assert payload["category_totals"] == {}
    assert payload["month_totals"] == {}
    assert payload["budget_alerts"] == []


def test_REQ_5_without_month_flag_json_matches_pre_month_filter_behavior(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,8.00\n"
        "2024-05-02,Food,Dinner,4.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\n", encoding="utf-8")

    result = _run_expenses_module(str(expenses_path), "--budgets", str(budgets_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload.keys()) == {
        "category_totals",
        "month_totals",
        "errors",
        "budget_alerts",
    }
    assert "month" not in payload
    assert payload["category_totals"] == {"Food": "12.00"}
    assert payload["month_totals"] == {"2024-05": "12.00"}
    assert payload["errors"] == []
    assert payload["budget_alerts"] == [
        {
            "month": "2024-05",
            "category": "Food",
            "total": "12.00",
            "limit": "10.00",
            "amount_over": "2.00",
        }
    ]


def test_REQ_6_budget_alerts_use_only_spending_in_selected_month(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,May,12.00\n2024-06-01,Food,June,20.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\n", encoding="utf-8")

    result = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--budgets",
        str(budgets_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["budget_alerts"] == [
        {
            "month": "2024-05",
            "category": "Food",
            "total": "12.00",
            "limit": "10.00",
            "amount_over": "2.00",
        }
    ]


def test_REQ_7_invalid_month_values_write_usage_and_exit_nonzero(tmp_path: Path):
    csv_path = _two_month_food_csv(tmp_path)
    invalid_month_values = (
        "2024-4",
        "202404",
        "2024-13",
        "2024-00",
        "2024/04",
    )

    for month_value in invalid_month_values:
        result = _run_expenses_module(str(csv_path), "--month", month_value)
        assert result.returncode != 0, month_value
        assert "usage" in result.stderr.lower(), month_value
        assert result.stdout.strip() == "", month_value


def test_REQ_8_month_flag_without_value_writes_usage_and_exits_nonzero(tmp_path: Path):
    csv_path = _two_month_food_csv(tmp_path)

    result = _run_expenses_module(str(csv_path), "--month")

    assert result.returncode != 0
    assert "usage" in result.stderr.lower()
    assert result.stdout.strip() == ""


def test_REQ_9_month_and_budgets_flags_may_appear_in_either_order(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,May,12.00\n2024-06-01,Food,June,20.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\n", encoding="utf-8")

    month_first = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--budgets",
        str(budgets_path),
    )
    budgets_first = _run_expenses_module(
        str(expenses_path),
        "--budgets",
        str(budgets_path),
        "--month",
        "2024-05",
    )

    assert month_first.returncode == 0, month_first.stderr
    assert budgets_first.returncode == 0, budgets_first.stderr
    assert json.loads(month_first.stdout) == json.loads(budgets_first.stdout)


def test_REQ_10_errors_list_still_includes_all_csv_validation_errors(tmp_path: Path):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-03-15,Food,Ok,5.00\n"
        "2024-04-01,,Bad category,7.00\n"
        "2024-05-01,Travel,,9.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path), "--month", "2024-03")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["category_totals"] == {"Food": "5.00"}
    assert payload["month_totals"] == {"2024-03": "5.00"}
    assert payload["errors"] == [
        {"line": 3, "reason": "empty category"},
        {"line": 4, "reason": "empty description"},
    ]


def test_py_20261005_lwd5_REQ_5_cli_merges_food_variants_under_first_row_spelling(
    tmp_path: Path,
):
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01, Food,Lunch,8.00\n"
        "2024-05-02,food,Dinner,4.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(csv_path))

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert set(payload["category_totals"].keys()) == {"Food"}
    assert "food" not in payload["category_totals"]
    assert payload["category_totals"]["Food"] == "12.00"


def test_py_20261005_lwd5_REQ_6_cli_duplicate_budget_categories_exit_nonzero(
    tmp_path: Path,
):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text(
        "category,limit\nFood,10.00\nfood,20.00\n",
        encoding="utf-8",
    )

    result = _run_expenses_module(str(expenses_path), "--budgets", str(budgets_path))

    assert result.returncode != 0
    assert result.stderr.strip() != ""
    assert result.stdout.strip() == ""


def test_py_20261005_lwd5_REQ_7_cli_month_and_budgets_use_expense_first_canonical_category(
    tmp_path: Path,
):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,FOOD,A,8.00\n2024-05-02,food,B,4.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\n Food ,10.00\n", encoding="utf-8")

    result = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--budgets",
        str(budgets_path),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["category_totals"] == {"FOOD": "12.00"}
    assert payload["budget_alerts"] == [
        {
            "month": "2024-05",
            "category": "FOOD",
            "total": "12.00",
            "limit": "10.00",
            "amount_over": "2.00",
        }
    ]


def test_REQ_11_file_errors_unchanged_when_month_flag_is_present(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n2024-05-01,Food,Lunch,8.00\n",
        encoding="utf-8",
    )
    missing_expenses = tmp_path / "missing-expenses.csv"
    missing_budgets = tmp_path / "missing-budgets.csv"
    bad_budgets = tmp_path / "budgets.csv"
    bad_budgets.write_text("category,limit\nFood,0\n", encoding="utf-8")

    missing_expense = _run_expenses_module(
        str(missing_expenses),
        "--month",
        "2024-05",
    )
    assert missing_expense.returncode != 0
    assert missing_expense.stderr.splitlines() == [str(missing_expenses)]
    assert "Traceback" not in missing_expense.stderr
    assert missing_expense.stdout.strip() == ""

    missing_budget = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--budgets",
        str(missing_budgets),
    )
    assert missing_budget.returncode != 0
    assert missing_budget.stderr.splitlines() == [str(missing_budgets)]
    assert "Traceback" not in missing_budget.stderr
    assert missing_budget.stdout.strip() == ""

    invalid_budget = _run_expenses_module(
        str(expenses_path),
        "--budgets",
        str(bad_budgets),
        "--month",
        "2024-05",
    )
    assert invalid_budget.returncode != 0
    assert invalid_budget.stderr.strip() == "invalid limit"
    assert invalid_budget.stdout.strip() == ""


def _expected_top_categories_from_payload(category_totals: dict[str, str], n: int) -> list[dict]:
    from factory_target_py.expenses import compute_top_categories

    decimal_totals = {key: Decimal(value) for key, value in category_totals.items()}
    ranked = compute_top_categories(decimal_totals, n)
    return [
        {
            "category": entry["category"],
            "total": money_to_json_string(entry["total"]),
        }
        for entry in ranked
    ]


def _multi_category_expenses_csv(tmp_path: Path) -> Path:
    csv_path = tmp_path / "expenses.csv"
    csv_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,30.00\n"
        "2024-05-02,Travel,Flight,50.00\n"
        "2024-05-03,Rent,Lease,50.00\n",
        encoding="utf-8",
    )
    return csv_path


def test_py_20261005_wa2k_REQ_4_cli_top_flag_prints_top_categories_json(tmp_path: Path):
    csv_path = _multi_category_expenses_csv(tmp_path)

    result = _run_expenses_module(str(csv_path), "--top", "2")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "top_categories" in payload
    assert payload["category_totals"] == {
        "Food": "30.00",
        "Travel": "50.00",
        "Rent": "50.00",
    }
    expected = _expected_top_categories_from_payload(payload["category_totals"], 2)
    assert payload["top_categories"] == expected
    assert payload["top_categories"] == [
        {"category": "Rent", "total": "50.00"},
        {"category": "Travel", "total": "50.00"},
    ]
    for entry in payload["top_categories"]:
        assert set(entry.keys()) == {"category", "total"}
        assert isinstance(entry["category"], str)
        assert isinstance(entry["total"], str)


def test_py_20261005_wa2k_REQ_4_cli_top_accepts_leading_zeros(tmp_path: Path):
    csv_path = _multi_category_expenses_csv(tmp_path)

    result = _run_expenses_module(str(csv_path), "--top", "02")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["top_categories"] == _expected_top_categories_from_payload(
        payload["category_totals"],
        2,
    )


def test_py_20261005_wa2k_REQ_5_cli_without_top_omits_top_categories_key(tmp_path: Path):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,Lunch,8.00\n"
        "2024-05-02,Food,Dinner,4.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\n", encoding="utf-8")

    without_top = _run_expenses_module(str(expenses_path), "--budgets", str(budgets_path))
    with_month = _run_expenses_module(str(expenses_path), "--month", "2024-05")

    assert without_top.returncode == 0, without_top.stderr
    assert with_month.returncode == 0, with_month.stderr
    payload_budgets = json.loads(without_top.stdout)
    payload_month = json.loads(with_month.stdout)
    assert "top_categories" not in payload_budgets
    assert "top_categories" not in payload_month
    assert set(payload_budgets.keys()) == {
        "category_totals",
        "month_totals",
        "errors",
        "budget_alerts",
    }
    assert set(payload_month.keys()) == {
        "category_totals",
        "month_totals",
        "errors",
        "month",
    }


def test_py_20261005_wa2k_REQ_6_cli_invalid_top_values_exit_without_success_json(
    tmp_path: Path,
):
    csv_path = _multi_category_expenses_csv(tmp_path)
    invalid_values = ("0", "-1", "abc", "1.5")

    for value in invalid_values:
        result = _run_expenses_module(str(csv_path), "--top", value)
        assert result.returncode != 0, value
        assert "invalid --top value" in result.stderr.lower(), value
        assert "positive integer" in result.stderr.lower(), value
        assert result.stdout.strip() == "", value


def test_py_20261005_wa2k_REQ_7_cli_top_flag_misuse_writes_usage_and_exits_nonzero(
    tmp_path: Path,
):
    csv_path = _multi_category_expenses_csv(tmp_path)

    top_last = _run_expenses_module(str(csv_path), "--top")
    duplicate_top = _run_expenses_module(str(csv_path), "--top", "2", "--top", "1")
    top_followed_by_flag = _run_expenses_module(
        str(csv_path),
        "--top",
        "--month",
        "2024-05",
    )

    for result in (top_last, duplicate_top, top_followed_by_flag):
        assert result.returncode != 0
        assert "usage" in result.stderr.lower()
        assert result.stdout.strip() == ""


def test_py_20261005_wa2k_REQ_8_cli_top_month_budgets_flags_order_independent(
    tmp_path: Path,
):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,May meal,30.00\n"
        "2024-05-02,Travel,May trip,50.00\n"
        "2024-06-01,Food,June meal,99.00\n",
        encoding="utf-8",
    )
    budgets_path = tmp_path / "budgets.csv"
    budgets_path.write_text("category,limit\nFood,10.00\nTravel,10.00\n", encoding="utf-8")

    top_first = _run_expenses_module(
        str(expenses_path),
        "--top",
        "2",
        "--month",
        "2024-05",
        "--budgets",
        str(budgets_path),
    )
    budgets_first = _run_expenses_module(
        str(expenses_path),
        "--budgets",
        str(budgets_path),
        "--month",
        "2024-05",
        "--top",
        "2",
    )

    assert top_first.returncode == 0, top_first.stderr
    assert budgets_first.returncode == 0, budgets_first.stderr
    assert json.loads(top_first.stdout) == json.loads(budgets_first.stdout)


def test_py_20261005_wa2k_REQ_9_cli_top_categories_respect_month_filter_and_errors(
    tmp_path: Path,
):
    expenses_path = tmp_path / "expenses.csv"
    expenses_path.write_text(
        "date,category,description,amount\n"
        "2024-05-01,Food,May,30.00\n"
        "2024-05-02,Travel,May,50.00\n"
        "2024-06-01,Rent,June,80.00\n",
        encoding="utf-8",
    )
    bad_budgets = tmp_path / "bad-budgets.csv"
    bad_budgets.write_text("category,limit\nFood,0\n", encoding="utf-8")
    missing_expenses = tmp_path / "missing-expenses.csv"

    filtered = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--top",
        "2",
    )
    assert filtered.returncode == 0, filtered.stderr
    filtered_payload = json.loads(filtered.stdout)
    assert filtered_payload["category_totals"] == {"Food": "30.00", "Travel": "50.00"}
    assert filtered_payload["top_categories"] == _expected_top_categories_from_payload(
        filtered_payload["category_totals"],
        2,
    )
    assert "Rent" not in {entry["category"] for entry in filtered_payload["top_categories"]}

    unreadable_expense = _run_expenses_module(
        str(missing_expenses),
        "--top",
        "2",
        "--month",
        "2024-05",
    )
    assert unreadable_expense.returncode != 0
    assert unreadable_expense.stderr.splitlines() == [str(missing_expenses)]
    assert unreadable_expense.stdout.strip() == ""

    invalid_month = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-13",
        "--top",
        "2",
    )
    assert invalid_month.returncode != 0
    assert "usage" in invalid_month.stderr.lower()
    assert invalid_month.stdout.strip() == ""

    invalid_budget = _run_expenses_module(
        str(expenses_path),
        "--budgets",
        str(bad_budgets),
        "--top",
        "2",
    )
    assert invalid_budget.returncode != 0
    assert invalid_budget.stderr.strip() == "invalid limit"
    assert invalid_budget.stdout.strip() == ""

    invalid_top = _run_expenses_module(
        str(expenses_path),
        "--month",
        "2024-05",
        "--top",
        "0",
    )
    assert invalid_top.returncode != 0
    assert "invalid --top value" in invalid_top.stderr.lower()
    assert invalid_top.stdout.strip() == ""
