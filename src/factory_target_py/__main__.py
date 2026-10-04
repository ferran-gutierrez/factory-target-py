from __future__ import annotations

import json
import sys
from pathlib import Path

from factory_target_py.expense_importer import import_expenses


def _result_to_json(result: dict) -> dict:
    return {
        "by_category": {key: str(value) for key, value in result["by_category"].items()},
        "by_month": {key: str(value) for key, value in result["by_month"].items()},
        "errors": result["errors"],
    }


def main() -> None:
    path = Path(sys.argv[1])
    csv_text = path.read_text(encoding="utf-8")
    result = import_expenses(csv_text)
    print(json.dumps(_result_to_json(result)))


if __name__ == "__main__":
    main()
