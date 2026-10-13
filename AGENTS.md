# AGENTS.md

## Working rules (required)

- Always make a plan before changing any code.
- Pure logic goes in `logic.py`, UI goes in `app.py`. Never mix them.
- Every new function in `logic.py` must have a test in `test_logic.py`.
- After every change, run `pytest` and fix until all tests pass.
- Use `zoneinfo` (stdlib) for time zones. The only extra libraries allowed are `streamlit` and `pytest` — do not import pandas/numpy/starlette/uvicorn (or anything else installed in `.venv`) in project code, even though they are installed.

## Repo status

- Layout: `logic.py` (pure logic), `test_logic.py` (logic tests), `test_app.py` (UI tests via Streamlit `AppTest`), `app.py` (Streamlit UI), `SPEC.md` (features + acceptance criteria). No git repo, no `pyproject.toml`/`requirements.txt`, no CI, no lint config yet.
- Run the app: `.venv/bin/streamlit run app.py` (server on localhost:8501).
- Do not invent architecture, commands, or conventions that are not present in the repo. As the project grows, update this file with verified commands.

## Python environment

- Virtualenv at `.venv/` (Python 3.13.12, created from miniconda's `python3.13`; `include-system-site-packages = false`).
- Use it explicitly: `.venv/bin/python`, `.venv/bin/pytest`, or `source .venv/bin/activate`.
- Base shell may be a conda environment; the venv does not inherit conda packages. Install dependencies into the venv (`.venv/bin/pip install ...`), not into conda.
- There is no lockfile or dependency manifest. Installed packages (via `.venv/bin/pip list`): streamlit 1.65, starlette 1.8, uvicorn 0.54, pytest 9.1, pandas 3.0, numpy 2.5, pyarrow, altair, requests, jsonschema, tzdata. If you add a dependency, consider creating `requirements.txt`/`pyproject.toml` to record it.
- Timezone quirk: `zoneinfo` resolves via the venv's `tzdata` package (no system zoneinfo on this machine's lookup path), and that package lacks some links — e.g. use `Asia/Makassar`, not `Asia/Denpasar`, for Bali. Verify a zone name with `.venv/bin/python -c "from zoneinfo import ZoneInfo; ZoneInfo('Asia/Makassar')"` before adding it.

## Testing

- Run all tests: `.venv/bin/pytest` (expect `19 passed` as of 2026-10-13; `test_logic.py` for pure logic, `test_app.py` for Streamlit `AppTest` UI tests).
- Run a single test: `.venv/bin/pytest test_logic.py::test_name -q`.
- Tests use fixed datetimes (e.g. October 2026) so DST boundaries (EU ends 2026-10-25, US ends 2026-11-01) are covered deterministically.

## Notes

- `.venv/.gitignore` ignores everything inside `.venv`, so the venv is safe to leave in place; when git is initialized, confirm `.venv/` is ignored.
