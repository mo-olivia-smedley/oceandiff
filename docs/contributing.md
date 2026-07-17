# Contributing

## Prerequisites

- Python 3.11+
- [conda](https://docs.conda.io/) or [venv](https://docs.python.org/3/library/venv.html)

---

## Set up a development environment

```bash
git clone https://github.com/olivia.smedley/oceandiff
cd oceandiff

conda create -n oceandiff-dev python=3.11 -y
conda activate oceandiff-dev
pip install -e ".[dev]"
```

---

## Running tests

```bash
pytest -q
```

---

## Code style

oceandiff uses [black](https://black.readthedocs.io/) for formatting:

```bash
black --target-version py311 oceandiff tests
```

Check only (as CI does):

```bash
black --check --target-version py311 oceandiff tests
```

Lint with [pylint](https://pylint.readthedocs.io/):

```bash
pylint oceandiff --disable=C0111,C0103,R0913
```

---

## Building the docs locally

Install the docs extras:

```bash
pip install -e ".[docs]"
```

Serve locally with live reload:

```bash
mkdocs serve
```

Build static HTML:

```bash
mkdocs build
```

---

## CI

GitHub Actions runs on every push and pull request to `main` and `develop`:

- `black --check` for formatting
- `pylint` for linting (non-blocking)
- `pytest -q` for tests
- `mkdocs gh-deploy` on pushes to `main` (deploys docs to GitHub Pages)
