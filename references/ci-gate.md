# CI gate generator (gen_ci.py, improvement #1)

`gen_ci.py --path <repo>` makes the audit *enforced*, not just tagged.

## What it produces
- `.github/workflows/audit.yml` — a GitHub Actions workflow that:
  1. checks out the repo
  2. sets up Python 3.11
  3. runs `python .mincode/gen_tests.py .` (generate smoke tests)
  4. runs `python -m unittest discover -s tests -v` (smoke tests)
  5. runs `python .mincode/audit.py .` as the gate — `audit.py` exits 1 on any
     HIGH finding, so the CI build FAILS. Zero tolerance by design.
- `.mincode/` — a copy of this skill's `scripts/` dropped into the target repo
  so the workflow is self-contained and portable.

## Deployment gotchas (learned the hard way)
1. **NEVER gitignore `.mincode/`.** The first cut of `gen_ci.py` appended
   `.mincode/` to `.gitignore`. That meant CI runners clone the repo WITHOUT
   the audit scripts → `python .mincode/audit.py` fails with "No such file".
   The scripts MUST be committed. `gen_ci.py` no longer touches `.gitignore`.
2. **Use relative paths in the generated YAML.** An early version embedded the
   absolute skill path (`C:\Users\...\scripts/*`) into the `cp` step. That path
   only exists on the author's Windows box and breaks on Linux CI runners.
   Generate `.mincode/` relative to the repo root and reference it as
   `python .mincode/audit.py .` in the workflow — no host-specific paths.
3. **`unittest discover` can pass vacuously.** In some envs (incl. the author's
   Windows setup) `python -m unittest discover -s tests` reports 0 tests even
   when test files exist (loader path quirks). The audit gate (exit 1 on HIGH)
   is the real enforcement; treat the test step as a best-effort smoke check,
   not the sole gate. Prefer `python tests/<mod>_test.py` for a reliable local
   run (see `references/test-generation.md`).
4. **Remind the user to commit `.mincode/` and `.github/`.** The generator
   prints this, but if the user only commits `audit.yml` and not `.mincode/`,
   CI still breaks. Both directories must be pushed.

## Usage
```bash
python scripts/gen_ci.py --path myapp
# commit + push .mincode/ and .github/ — CI now fails on any HIGH vuln
```

## Why it closes a loop
`audit.py` (improvement #6) tags `audit-clean-<date>` on a clean pass, but a
tag alone does not stop a HIGH finding from being merged. The CI gate makes the
audit a hard requirement on every push/PR — the skill's core non-negotiable
("audit every project before declaring done") is now machine-enforced.
