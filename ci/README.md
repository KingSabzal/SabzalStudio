# Continuous integration

`github-actions-ci.yml` is the workflow for this project. It is parked here
rather than in `.github/workflows/` because the token used to push this branch
is not allowed to create workflow files.

To turn it on, move it into place and push:

```bash
mkdir -p .github/workflows
git mv ci/github-actions-ci.yml .github/workflows/ci.yml
git commit -m "Enable CI"
git push
```

## What it checks

On Python 3.10, 3.11 and 3.12:

1. **`compileall`** — everything parses.
2. **`ruff check`** — undefined names, unused imports, unused variables and
   the bugbear rules. Configured in `pyproject.toml`.
3. **`pytest`** — the suite in `tests/`.
4. **A credential check** — fails the build if `config.json` or `.env` is ever
   tracked by git, since both hold API keys in plain text.

Torch is deliberately not installed: it is roughly 800 MB and no test needs a
model. Only the packages the tested modules import are installed.

## Running the same checks locally

```bash
pip install pytest ruff
python -m compileall -q utility app.py
python -m ruff check .
python -m pytest tests -q
```

## Why this exists

The two defects that stopped the project producing any video at all — a
function called with an argument its signature did not accept, and a pinned
Pillow version that removed a constant MoviePy still used — were both the kind
a ten-line test catches immediately. There was no test suite and no CI, so
neither was noticed.
