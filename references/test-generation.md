# Test generation & execution — gotchas

## Why `discover` reports 0 tests
`python -m unittest discover -s tests` can report 0 tests in some Windows/envs
due to a loader path quirk. Do NOT trust a green "Ran 0 tests" — it usually
means the loader never found the files, not that there's nothing to test.

Reliable patterns, in order:
1. **Direct file run** — `python tests/<mod>_test.py` (uses `unittest.main()`).
   This is what `gen_tests.py` generates and what `audit.py --run-tests` runs.
2. **Module path** — `python -m unittest tests.<mod>_test`.
3. `discover` only as a last resort.

## `from src import x` fails when running a test file directly
ModuleNotFoundError: No module named 'src'. The test file runs as a top-level
script, so `src/` is not on `sys.path`. Two fixes:
- **Inject PYTHONPATH** (preferred, what `audit.py --run-tests` does): run each
  `tests/*_test.py` via `subprocess.run([py, tf], cwd=root, env={**os.environ,
  "PYTHONPATH": root})`.
- Or add a `sys.path.insert(0, project_root)` shim at the top of the generated
  test file.

`audit.py --run-tests` implementation: `glob.glob("tests/*_test.py")` →
subprocess per file, `cwd=root`, `PYTHONPATH=root` → parse `Ran N test` and
`FAILED (failures=M, errors=K)` to compute pass/fail. Copy this wherever you
need to execute generated tests.

## Self-scan false positives
`audit.py`'s regexes for `eval(` / `exec(` match the *literal pattern-definition
strings* inside `audit.py` itself. So when you audit a repo that contains the
skill scripts (e.g. `.mincode/` dropped by `gen_ci.py`), those lines emit fake
HIGH CWE-95 findings. Keep `.mincode` in `SKILL_DIRS`/`SKIP_DIRS` — never remove
it or every `gen_ci.py`-using repo flags itself.

## CI gate note
`gen_ci.py` writes `.mincode/` + `.github/` into the target repo. Commit
`.mincode/` — do NOT gitignore it, or the CI checkout lacks the scripts and
`python .mincode/audit.py` fails with "No such file". The generated YAML uses
relative paths (`.mincode/...`), never absolute Windows paths (they break Linux
CI runners).
