# gen_tests.py — test generation gotchas

Condensed from real debugging while building `scripts/gen_tests.py`.

## Why `discover` reports 0 tests
`python -m unittest discover -s tests` reported "Ran 0 tests" in the test env
despite valid `def test_*` functions. Cause: unittest loader path quirk when
`tests/` is treated as a top-level dir and `from src import x` can't resolve.
Reliable invocation: `python tests/<mod>_test.py` (the generated file ends with
`if __name__ == "__main__": unittest.main()`). Also works:
`python -m unittest tests.<mod>_test`.

## Make `from src import x` resolve in the generated test
Inject a `__file__`-relative path insert at the TOP of every generated test
(before the import), for both pytest and unittest renders:
```python
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src import <module>
```
Do NOT rely on a `tests/__init__.py` or a `rootshim.py` shim — those fail to
load under `discover` because the package import order isn't guaranteed.

## Scan rules
- Skip `__init__.py` AND `__main__.py` when iterating `src/` — `__main__.py`
  is an entry point, not a module to unit-test, and it pollutes `tests/`.
- Default framework is `unittest` (stdlib, zero-dep). pytest is often not
  installed, so don't default to it.
- Skip modules that already have a test file (idempotent re-run).
- One smoke test per public top-level symbol (function/class not starting `_`):
  `assert callable(...)` for funcs, `assert isinstance(..., type)` for classes.
  Leave a `# TODO: call ... with minimal inputs` so the human fills real asserts.

## Workflow
Run after `proj_gen.py`, before `audit.py`:
```bash
python scripts/gen_tests.py myapp
python tests/svc_test.py        # fills the "minimal != untested" gate
```
