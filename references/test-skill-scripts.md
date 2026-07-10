# Testing the skill's own scripts (Windows + git-bash)

When iterating on `scripts/*.py` you need to import / run them directly to unit
test a function. On this host (Windows 10, git-bash/MSYS shell, **native Windows
Python 3.11**) three traps recur — capture them so the next session doesn't burn
~10 tool calls rediscovering them.

## Trap 1 — native Python does NOT understand MSYS paths
Git-bash mounts `C:` as `/c/` and `D:` as `/d/`. The **shell** expands these, but
**native Windows Python does not**. So:
```python
sys.path.insert(0, "/d/mincode-vuln-arch/scripts")   # FAILS in python: path not found
import audit                                          # ModuleNotFoundError
```
Fix: use **Windows-style paths** inside Python code — forward slashes are fine,
just keep the drive letter:
```python
sys.path.insert(0, "D:/mincode-vuln-arch/scripts")    # works
import audit
```
Rule of thumb: in `terminal` shell commands `/d/...` is OK (shell expands it);
inside a `python -c` / `python - <<'EOF'` block use `D:/...`.

## Trap 2 — single-quoted `$SKILL` is never expanded
In bash, `'$SKILL'` is literal — the variable stays `$SKILL` and the import fails.
```bash
python -c "import sys; sys.path.insert(0,'$SKILL'); import audit"   # SKILL is literal -> fail
```
Fix: use **double quotes** so bash expands `$SKILL`, or better — copy the script
into the current working dir and import it locally (no path games):
```bash
cp /d/mincode-vuln-arch/scripts/audit.py .
python - <<'EOF'
import audit
print(audit.run_tests("."))
EOF
rm -f audit.py
```

## Trap 3 — `importlib` from a temp absolute path under /tmp fails
`/tmp` does not exist on Windows. Writing a copy to `/tmp_x.py` raises
`Permission denied`. Write the temp copy into the **current working dir** instead.

## Reliable unit-test recipe (use this)
```bash
cd "$USERPROFILE/_some_scratch"
cp /d/mincode-vuln-arch/scripts/sample_repo.py .      # or audit.py / gen_tests.py
python - <<'EOF'
import sample_repo as s
print(s.detect_stack_hints("."))
print(s.apply_arch_table("skill_test.md", ["Storage"]))
EOF
rm -f sample_repo.py skill_test.md
```
- `cp` into cwd → import works with zero path fiddling.
- Pass the SKILL.md under test as a normal file in cwd (e.g. `skill_test.md`),
  not the live one, so you can mutate it without touching the real skill.
- Clean up the copies afterwards (separate `rm` call — never bundle `rm -rf`
  with other steps; the consent gate blocks it).

## End-to-end CLI test (no import tricks)
Just run the script with absolute D:/ paths and pipe through `head`:
```bash
SKILL=/d/mincode-vuln-arch/scripts
python "$SKILL/audit.py" "$USERPROFILE/_mc_poly" --sarif sarif.json 2>&1 | head -3
```
This exercises the real `main()` (argparse, findings loop, outputs) better than a
unit import for flag-addition work.

## Bonus: the `<<'EOF'` heredoc detail
`python - <<'EOF'` (quoted delimiter) passes the block verbatim to python — shell
does NOT expand `$VAR` inside it. So a literal `$SKILL` inside such a block stays
`$SKILL`. Either export the var first and reference it unquoted in the Python
string, or avoid heredocs and use `python -c "..."` with double-quoted shell
expansion. The cwd-`cp` recipe above sidesteps all of this.
