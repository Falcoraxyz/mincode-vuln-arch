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

## Test file must call `unittest.main()` (or the run is silent)
A `tests/<mod>_test.py` that only defines `class TestX(unittest.TestCase)` and
`from src import mod` but has **no `if __name__ == "__main__": unittest.main()`**
produces ZERO output when run directly (`RC=0`, empty stdout/stderr) — so
`run_tests()` sees no `Ran N test` line and counts it as 0 tests, silently
"passing". Always emit the `unittest.main()` runner (gen_tests does). When
hand-writing a fixture test to exercise `audit.py --run-tests`, remember the
runner line or the gate will vacuously pass.

## Assertion-aware generation (#8)
`gen_tests.py` reads each function's **return annotation** via `ast` and emits a
*meaningful* stub, not a pass-through smoke body:
- Typed dummy args from the signature: `int→0`, `str→""`, `list→[]`,
  `dict→{}`, `tuple→()`, `bool→False`, `bytes→b""`, `set→set()`, else `None`.
- `assert isinstance(result, <ret_type>)` when the return annotation is a simple
  name (e.g. `int`, `str`); otherwise `assert result is not None` (with the
  expected return type in a comment) — covers `List[int]`, `Optional[str]`, etc.
- Classes: instantiate with typed dummy ctor args + `isinstance(obj, Cls)` +
  `hasattr(obj, <public_method>)` per public method.

This makes `audit.py --run-tests` actually catch a wrong return type / broken
computation (e.g. `add` returning `str` fails `isinstance(result, int)` → MED
CWE-1120, grade drop, gate fails) instead of passing through.

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
