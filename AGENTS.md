# AGENTS.md

## Development workflow

- **Run tests**: `python -m pytest tests -q`
  Do NOT use `make tests`: the target name collides with the `tests/` folder, so make answers "tests is up to date" and runs nothing.
- **Run tests with coverage**: `python -m pytest tests --cov`
- **Install dev dependencies**: `make install-dev`
- **Format code**: `make format` (runs isort + black)
- **Lint code**: `make lint` (uses pylint)

## Windows specifics (this machine)

- Python 3.12.10 is installed. Use `py -3.12`; the default `python` on PATH is also 3.12.
- Keep the project at `C:\ai-course\python-package-boilerplate`. A longer path breaks `shapely`/`geopandas` with `ImportError: DLL load failed ... file name or extension is too long` (Windows MAX_PATH).
- The virtual environment already exists in `.venv` (Python 3.12.10). Activate it with `.\.venv\Scripts\Activate.ps1`.
- Do NOT run `make venv` or `make build`: the Makefile calls `python3`, which on this machine resolves to Python 3.14 instead of the project's 3.12.
- Test dependencies: `pip install -e ".[tests]"`. The extra is named `tests`, not `test`, so `make install-test` installs nothing.

## Package structure

- **Main code**: `my_package/` directory contains the library
- **Entrypoint**: `my_package/my_module.py` defines public API (`MyClass`, `my_function`)
- **Version**: read at import time via `importlib.metadata` in `my_package/__init__.py` (the module must be imported as `importlib.metadata`), auto-managed by setuptools_scm from pyproject.toml
- **Package name**: `my_package` (matches pyproject.toml name)

## Examples & testing

- **Python examples**: `hello.py` (simple script), `density.py` (population density, function with docstrings)
- **Jupyter example**: `examples/my_example.ipynb`, data in `examples/data/`
- **Test structure**: `tests/test_1.py`, pytest fixtures
- **pytest source**: comes from the `tests` extra, not from `dev`

## CI/CD workflow

- **Tests**: `.github/workflows/tests.yml`
- **Documentation**: `.github/workflows/documentation.yml`
- **PyPI release**: `.github/workflows/pypi.yml` (triggers on git tags)

## Package configuration

- **Python version**: `requires-python = ">=3.10"` in pyproject.toml; the course requires 3.11/3.12, this project runs 3.12.10
- **Main dependency**: geopandas>=1.0.0,<2.0.0
- **Dev tools**: black, isort, pylint, pre-commit, jupyter, build, twine
- **Documentation**: Sphinx sources in `docs/`; build with `docs/make.bat` (Windows)

## Project quirks

- **Editable install**: `pip install -e ".[dev]"` (this is what `make install-dev` does)
- **Code style**: black line-length=120, isort configured
- **Linting**: pylint max-line-length=120
- **Version scheme**: post-release from setuptools_scm
- **Data location**: example data in `examples/data/`

## Local setup

- **Clean build artifacts**: `make clean`
- **Build package**: `python -m build .` (not `make build`, see Windows specifics)