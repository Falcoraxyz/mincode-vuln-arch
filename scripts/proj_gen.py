#!/usr/bin/env python3
"""Scaffold a minimal, modular project skeleton with audit + hash-chain hooks.
Usage: python proj_gen.py <project_name> [--path <dir>]
Creates: src/ tests/ docs/ README.md CHANGELOG.md
"""
import argparse, os, sys, textwrap, datetime

README = """# {name}

Minimal modular project. Stdlib-first. One concern per module.

## Layout
- `src/`  one module per concern, thin public API
- `tests/` one test file per module
- `docs/` architecture + decisions

## Run
```
python -m src
```

## Audit
```
python <skill>/scripts/audit.py .
```
"""

CHANGELOG = """# Changelog (hash-chain anchored)

Append entries; each links to vault note via `chain_hash`.
- {date}  init  scaffold created by mincode-vuln-arch
"""

ARCH = """# Architecture

Stack decision recorded here. See mincode-vuln-arch Architecture Decision table.

- Chosen: <fill>
- Why: <fill>
- Alternatives rejected: <fill>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("name")
    ap.add_argument("--path", default=".")
    a = ap.parse_args()
    root = os.path.join(os.path.abspath(a.path), a.name)
    os.makedirs(root, exist_ok=True)
    for d in ("src", "tests", "docs"):
        os.makedirs(os.path.join(root, d), exist_ok=True)
    # minimal src entry
    with open(os.path.join(root, "src", "__init__.py"), "w") as f:
        f.write(f'"""Public API for {a.name}."""\n\n__version__ = "0.1.0"\n')
    with open(os.path.join(root, "src", "__main__.py"), "w") as f:
        f.write('def main():\n    print("ok")\n\n\nif __name__ == "__main__":\n    main()\n')
    with open(os.path.join(root, "tests", "test_smoke.py"), "w") as f:
        f.write('def test_smoke():\n    assert True\n')
    date = datetime.date.today().isoformat()
    with open(os.path.join(root, "README.md"), "w") as f:
        f.write(README.format(name=a.name, date=date))
    with open(os.path.join(root, "CHANGELOG.md"), "w") as f:
        f.write(CHANGELOG.format(date=date))
    with open(os.path.join(root, "docs", "architecture.md"), "w") as f:
        f.write(ARCH)
    print(f"scaffolded: {root}")
    print("next: fill src/, run audit.py, then hashchain.py append <note>")


if __name__ == "__main__":
    main()
