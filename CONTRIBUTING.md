# Contributing to wdpa-mcp

Thank you for contributing to `wdpa-mcp`!

## Code Quality Standards

1. Use `uv` for package management and virtual environment maintenance.
2. Code style is enforced using `ruff`:
   ```bash
   uv run ruff format src tests scripts
   uv run ruff check --fix src tests scripts
   ```
3. Test suite must maintain at least 90% branch coverage:
   ```bash
   uv run pytest --cov=wdpa_mcp --cov-branch --cov-report=term-missing
   ```
4. Build and run distribution check and smoke test before submitting PRs:
   ```bash
   uv build
   uv run python scripts/check_dist.py
   uv run --no-project --with ./dist/wdpa_mcp-0.1.0-py3-none-any.whl python scripts/smoke.py
   ```
