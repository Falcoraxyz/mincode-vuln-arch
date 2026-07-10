#!/usr/bin/env python3
"""Build a single-file, zero-dependency `mincode.pyz` distribution.

Bundles the toolkit into one runnable archive (Python 3.8+ stdlib `zipapp`):
    python build_pyz.py            -> produces mincode.pyz
    python mincode.pyz audit .     # runs anywhere, no pip, no install

How it works:
- `scripts/` is copied verbatim into the archive root (so `import config` works).
- `mincode.py` is renamed to `__main__.py` (the zipapp entry point).
- A shebang + pyz magic makes `./mincode.pyz` executable on Unix.

Zero third-party deps. Output is cross-platform (Windows/Linux/macOS) as long as
a Python 3.8+ interpreter is present.
"""
import os
import shutil
import zipapp
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(HERE, "scripts")
ENTRY = os.path.join(HERE, "mincode.py")
OUT = os.path.join(HERE, "mincode.pyz")


def main():
    if not os.path.isdir(SCRIPTS):
        raise SystemExit(f"scripts/ not found at {SCRIPTS}")
    if not os.path.isfile(ENTRY):
        raise SystemExit(f"mincode.py not found at {ENTRY}")

    build = tempfile.mkdtemp(prefix="mincode_build_")
    try:
        # 1. copy scripts/ -> <build>/scripts  (mincode.py resolves SCRIPTS = HERE/scripts)
        shutil.copytree(SCRIPTS, os.path.join(build, "scripts"))
        # 2. mincode.py -> __main__.py (zipapp entry)
        shutil.copy(ENTRY, os.path.join(build, "__main__.py"))
        # 3. reference config example
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
