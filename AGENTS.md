# factory-target-py

A minimal Python package in src layout, tested with pytest and linted and formatted with ruff. Work arrives as factory tasks; `.factory/contract.json` defines the checks that decide pass or fail.

## Stack
Language: Python 3.12 · Packaging: `pyproject.toml` (setuptools) · Tests: pytest · Lint and format: ruff

## Commands
- Install: `python -m pip install -e '.[dev]'`
- Lint: `ruff check .`
- Format check: `ruff format --check .` (fix with `ruff format .`)
- Tests: `pytest -q`

## Layout
- The package lives in `src/factory_target_py/`. New modules go inside it.
- Tests live in `tests/test_*.py` and import the package by name.
- Specs live in `specs/`.

## Rules
- Changes stay inside `src/**`, `tests/**`, `specs/**` and `pyproject.toml`.
- Do not edit `ruff.toml`, `pytest.ini`, any `conftest.py`, `.factory/**`, `.github/**` or `AGENTS.md`.
- Runtime code uses the standard library only; new runtime dependencies need a clear reason in the spec.
- No secrets and no network access at runtime.
