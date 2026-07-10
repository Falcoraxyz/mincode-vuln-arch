# mincode-vuln-arch — gotchas & operational notes

## Hash-chain ordering (critical)
- Only **hand-authored** notes are chained: `Audit-*`, `Template-*`, and any
  manually created note.
- **Auto-generated** notes — `vault/Index.md` (`vault_index.py`) and
  `vault/Common-Mistakes.md` (`cross_learn.py`) — MUST NOT be appended to the
  chain. They are regenerated on every run; chaining them makes every
  subsequent `hashchain.py verify` report a false TAMPER.
- Correct workflow: `append` the hand-authored notes FIRST, THEN run
  `vault_index.py` and `cross_learn.py` to (re)generate the auto notes.

## Running generated tests on Windows
- `python -m unittest discover -s tests` returns 0 tests in this env (loader
  quirk). Run a generated suite with `python tests/<mod>_test.py`
  (unittest.main in `__main__`) or `python -m unittest tests.<mod>_test`.
- Tests are generated with `sys.path.insert` so `from src import x` resolves
  when run from the project root.

## Moving / relocating the skill (Windows)
- To make Hermes load the skill from a non-standard path, create a directory
  junction to the repo:
  `subprocess.run(["cmd","/c","mklink","/J", skill_dir, repo_dir], shell=True)`.
- Do NOT use bash `cmd //c "mklink /J a b"` — quotes get stripped and it fails
  silently. A `.bat` wrapper also swallows the error. `subprocess`+`shell=True`
  is the reliable path.

## audit.py scope
- `tests/` is skipped by the scanner (generated TODOs would false-flag CWE-1078).
- A fully clean audit tags `audit-clean-<date>`; scaffold tags `scaffold-<date>`.

## sample_repo.py
- Snippet extraction skips test files, `__init__.py`, `__main__.py`; max 4
  public symbols per module. Writes `## Reusable snippets` to the vault
  `Template-<name>.md` and a local `docs/snippets.md`.
