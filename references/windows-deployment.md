# Windows deployment + gotchas (mincode-vuln-arch)

## Relocate skill + vault to another drive (e.g. D:) while keeping Hermes loading it
- Copy the whole skill dir to `D:\mincode-vuln-arch` (scripts/ + vault/ + SKILL.md).
- Remove the Hermes skills copy and create a **junction** (not a symlink):
  - `cmd /c mklink /J "a" "b"` run from git-bash STRIPS quotes → silently fails.
  - Reliable:
    `python -c "import subprocess; subprocess.run('cmd /c mklink /J \"<hermes_skill_path>\" \"<D:path>\"', shell=True)"`
  - Alt: write a tiny `.bat` that runs `mklink /J ...` and call it via
    `cmd /c file.bat` (bat stdout is NOT captured by git-bash, but the link is made).
- Update `OBSIDIAN_VAULT_PATH` in `%HERMES_HOME%\.env` to the new
  `D:/.../vault` (forward slashes).
- Verify: `test -e "$HERMES_HOME/skills/.../mincode-vuln-arch/SKILL.md"`.

## hashchain.py — re-append false-TAMPER bug
- `append` MUST strip any existing YAML frontmatter from the note body BEFORE
  computing sha256 + HMAC. Else stored `chain_hash` is from raw body but
  `verify` reads the frontmatter'd body → false TAMPER on every re-append.
- Compute hash + HMAC over the FINAL on-disk bytes (frontmatter included),
  and write frontmatter only after the body is final.

## Cross-drive relpath
- `os.path.relpath(note, vault)` raises `ValueError` across C:/D: on Windows.
  Fallback to `os.path.abspath(note)` inside try/except ValueError.

## Running generated tests (unittest, zero-dep)
- `python -m unittest discover -s tests` returns **0 tests** in this
  git-bash/uv env (loader quirk with top-level `tests/` dir). Run the file
  directly instead: `python tests/<module>_test.py`
  (runs `unittest.main()` via `__main__` guard).
- Or `python -m unittest tests.<module>_test` from the project root.

## pip-audit dependency scan
- Pass each dep file per-file (`-r file`); matching only the first file
  misses the others (pyproject.toml vs requirements.txt).
- When `pip-audit` is absent, emit a LOW `CWE-1104` notice — do NOT fail.
