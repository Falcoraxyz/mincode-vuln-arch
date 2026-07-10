# audit.py output formats & maintenance pitfalls

Concrete recipes distilled from extending `audit.py` with `--sarif`, `--run-tests`,
`--report`, and `#8` assertion-aware test generation. Read before editing `main()`
or adding a new output target.

## 1. Adding a new output format (SARIF / HTML / future)

Implement as a PURE function, separate from `main()`. Shape that worked:

```python
def to_<fmt>(findings, scanned_path, grade, penalty, high, cwes):
    # build string/doc from `findings` + the ALREADY-computed scalars.
    # never recompute grade inside here.
    return rendered
```

Call it in `main()` AFTER these two lines exist and have run:
```python
g, penalty = grade(findings)          # fills grade + penalty
# ... findings loop that fills `high` and `cwes` (see §3) ...
if a.report:
    open(a.report, "w").write(to_html(findings, path, g, penalty, high, cwes))
```
Calling before `grade()` runs yields a wrong/blank badge. The function must read
`findings` plus the passed scalars only.

Reference implementations: `to_sarif()` (rules keyed by CWE id, `security-severity`
per level, `artifactLocation.uri` = relative path with `/` separators) and
`to_html()` (inline CSS, severity badge colors via a `SEV_COLOR` dict, A-F grade
badge color map, CWE links to `https://cwe.mitre.org/data/definitions/<num>.html`).
Both are self-contained, zero-dep.

## 2. The `main()` regression trap (EDIT CAREFULLY)

`audit.py main()` has ONE loop that does three jobs at once:
```python
for sev, fp, ln, desc, cwe, snip in findings:
    if sev == "HIGH":
        high += 1
    cwes.add(cwe)                                  # <-- needed for SARIF + summary
    print(f"[{sev}] {fp}:{ln}  {desc}  [{cwe}]  | {snip}")   # <-- user output
```
When adding a flag/branch, a patch that re-indents or splits this block can DROP the
`cwes.add(...)` + `print(...)` lines. Symptom: grade still prints, but `CWEs:` is
empty and SARIF rule `shortDescription` goes blank — silent data loss.

Guardrail: after any `main()` edit, verify with a repo containing BOTH a HIGH and a
MED finding that (a) both lines print, (b) `CWEs: CWE-xxx, CWE-yyy` is non-empty.

## 3. Proving `--run-tests` actually fails (fixture recipe)

`run_tests()` globs `tests/*_test.py`, runs each via `subprocess` with
`env["PYTHONPATH"] = root` (so `from src import x` resolves), and parses
`Ran N test` / `FAILED (failures=M, errors=K)` from stdout/stderr.

A hand-written fixture MUST:
- end with `if __name__ == "__main__": unittest.main()` — without it the file
  produces NO `Ran N tests` line, `run_tests()` sees 0 tests, and the gate passes
  VACUOUSLY (hides the failure).
- carry a REAL assertion that breaks when the impl is wrong, e.g.:
  ```python
  def test_add(self):
      result = calc.add(0, 0)
      self.assertIsInstance(result, int)   # breaks if add() returns str
  ```
To demonstrate the gate fails: make `src` return the wrong type -> `isinstance`
fails -> MED CWE-1120 -> grade drops (C) -> exit 1. (Clean impl: exit 0, A.)

## 4. `--run-tests` gate semantics

`blocked = high or (a.run_tests and failed_count > 0)` -> `sys.exit(1 if blocked)`.
So with `--run-tests`, ANY test failure fails the audit gate (not just HIGH vulns).
This is what enforces "minimal != untested" in CI. The CI workflow runs
`audit.py . --sarif sarif.json --report audit-report.html --run-tests`.
