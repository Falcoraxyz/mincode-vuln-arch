# Self-test gotchas when extending mincode-vuln-arch (Windows / git-bash)

Patterns that bit during development. Apply whenever you write a script under
`scripts/` and then test it from a `terminal` call.

## 1. `$SKILL` / path vars inside single-quoted heredocs do NOT expand
Bash single quotes (`<<'EOF'`) suppress `$VAR` expansion. A line like
`sys.path.insert(0, '$SKILL')` stays literal `'/d/mincode-vuln-arch/scripts'`
and `import audit` fails with `ModuleNotFoundError`.
- Fix A: use double quotes in the heredoc delimiter (`python - <<"EOF"`) only if
  you actually want expansion — but then `$` in Python f-strings/regex also
  expands, which corrupts them.
- Fix B (preferred): copy the script into the cwd first (`cp $SKILL/audit.py .`)
  then `python - <<'EOF'` with a plain `import audit` (no sys.path needed).
- Fix C: pass the absolute path as a real arg, not via env interpolation inside
  the heredoc.

## 2. `/d/...` vs `D:/...` in Python `open()` inside a `terminal` heredoc
`/d/mincode-vuln-arch/SKILL.md` resolves fine from the shell (`ls` works) but
`open("/d/mincode-vuln-arch/SKILL.md")` inside a Python heredoc sometimes raises
`FileNotFoundError` (MSYS path translation is inconsistent for `open()`).
- Fix: use the Windows form `r"D:\mincode-vuln-arch\SKILL.md"` (or `os.path`
  join) when passing paths into Python `open()` / `importlib`. Shell-level
  commands still prefer `/d/...` or `$HOME` style.

## 3. `import audit` fails when the script lives on a different drive via sys.path
Even with `sys.path.insert(0, '/d/mincode-vuln-arch/scripts')`, a heredoc
`import audit` can fail. The reliable dev loop is:
```
cp /d/mincode-vuln-arch/scripts/audit.py .
python - <<'EOF'
import audit
print(audit.some_func(...))
EOF
rm -f audit.py
```
(do NOT leave the copied script in the project — it pollutes `audit.py` scans
and the CI bundle).

## 4. When testing `audit.py` on a project that has `.mincode/`, add `.mincode` to SKIP_DIRS
`gen_ci.py` copies the scripts into `.mincode/`. If you re-run `audit.py` on that
same project, it scans its OWN source (`eval(`/`exec(` regex) and reports false
HIGHs. Always skip `.mincode` (and `tests`, `node_modules`, etc.). See
`SKIP_DIRS` in `audit.py`.

## 5. `unittest discover` reports 0 tests on Windows — run each file directly
`python -m unittest discover -s tests` frequently yields "Ran 0 tests" from a
subprocess even when `tests/*_test.py` exist. Run each file with `unittest.main()`
and count by parsing `Ran N test` / `FAILED (failures=M, errors=K)`. (Full
detail in `references/engineering-notes.md`.)

## 6. PYTHONPATH for `from src import X` inside generated tests
Running `python tests/calc_test.py` fails with `ModuleNotFoundError: No module
named 'src'` unless the project root is on the path. Either put
`sys.path.insert(0, project_root)` at the top of the test file, or invoke the
test subprocess with `env["PYTHONPATH"] = project_root`.
