#!/usr/bin/env python3
"""Build a single-file, zero-dependency `mincode.pyz` distribution.

Bundles the toolkit into one runnable archive (Python 3.8+ stdlib `zipapp`):
    python build_pyz.py            -> produces mincode.pyz
    python mincode.pyz audit .     # runs anywhere, no pip, no install

How it works:
- All scripts/*.py are copied FLAT to the archive root, so `import config`
  (and every sibling script) resolves at the zip root.
- scripts/cli.py becomes __main__.py (the zipapp entry point). It already knows
  to treat its own dir as the scripts dir.
- A shebang makes `./mincode.pyz` executable on Unix.

Zero third-party deps. Cross-platform (Windows/Linux/macOS) on Python 3.8+.
"""
import os
import shutil
import zipapp
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "scripts")
CLI = os.path.join(SCRIPTS, "cli.py")
OUT = os.path.join(HERE, "mincode.pyz")


def main():
    if not os.path.isfile(CLI):
        raise SystemExit(f"scripts/cli.py not found at {CLI}")

    build = tempfile.mkdtemp(prefix="mincode_build_")
    try:
        # flatten scripts/*.py -> <build>/  (import config resolves at zip root)
        for fn in os.listdir(SCRIPTS):
            if fn.endswith(".py") and not fn.startswith("__"):
                shutil.copy(os.path.join(SCRIPTS, fn), os.path.join(build, fn))
        # cli.py -> __main__.py (zipapp entry; it treats its dir as the scripts dir)
        shutil.copy(CLI, os.path.join(build, "__main__.py"))
        ex = os.path.join(HERE, "mincode.toml.example")
        if os.path.isfile(ex):
            shutil.copy(ex, os.path.join(build, "mincode.toml.example"))

        zipapp.create_archive(
            source=build,
            target=OUT,
            interpreter="/usr/bin/env python3",
        )
        size = os.path.getsize(OUT)
        print(f"[pyz] built {OUT} ({size} bytes)")
        print("     run:  python mincode.pyz audit <project> --no-vault")
    finally:
        shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    main()
