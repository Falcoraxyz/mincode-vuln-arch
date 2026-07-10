# Engineering notes — extending mincode-vuln-arch

Non-obvious techniques + pitfalls hit while building the toolkit. Read this
before editing `scripts/*.py` (especially `audit.py`, `gen_tests.py`,
`gen_ci.py`, `llm_review.py`).

## Running generated tests on Windows
`python -m unittest discover -s tests` frequently reports **0 tests run** from a
subprocess even when `tests/*_test.py` exist (loader path quirk on
Windows/MSYS-git-bash). Do NOT use it as a gate. Run each file directly:

    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    subprocess.run([sys.executable, test_file], cwd=root, env=env, ...)

with `unittest.main()` at the bottom of every generated test file. Count results
by parsing stdout+stderr for `Ran N test` and
`FAILED (failures=M, errors=K)`.

## PYTHONPATH for `from src import X`
Generated tests import the project as a package (`from src import calc`). Running
a test file directly needs `PYTHONPATH=<project root>` injected (prepend any
existing value) or you get `ModuleNotFoundError` and a silent 0-test pass-through.

## CI gate: never gitignore `.mincode/`
`gen_ci.py` copies `scripts/` into the target repo as `.mincode/` so the workflow
is self-contained. If `.mincode/` ends up gitignored, CI clones without the audit
scripts and the gate silently can't run. A `.gitignore` patch that adds
`.mincode/` is a BUG — keep it tracked/committed.

## Cross-drive relative paths
`os.path.relpath(a, b)` raises `ValueError` when `a` and `b` are on different
drives (e.g. D: vault vs C: repo). Always wrap in try/except and fall back to the
absolute path when building SARIF `artifactLocation.uri` / HTML `location`.

## Local LLM auto-detect (offline-first)
To review without an API key, probe local OpenAI-compatible servers before the
cloud: `GET {base}/v1/models` with a ~2s timeout; HTTP 200 -> use that endpoint
with a dummy bearer token. Precedence: explicit `OPENAI_BASE_URL`/`OPENAI_API_KEY`
-> Ollama (`localhost:11434/v1`) -> llama.cpp (`localhost:8080/v1`) -> OpenAI cloud.
No backend reachable -> safe no-op (exit 0), never a hard error.

## Editing long scripts with the patch tool
When a `patch` returns "file last read with offset/limit pagination (partial
view)", re-read the WHOLE file before the next overwrite. A multi-hunk edit can
silently drop lines outside the shown window — e.g. one edit to `audit.py` deleted
the `for sev, ...: cwes.add(cwe); print(...)` loop, so test-failure CWEs stopped
appearing in output. After big patches, grep the loop body to confirm the
print/accumulate lines survived.

## SARIF shape that GitHub code scanning accepts
- `version: "2.1.0"`, `$schema` pointing at schemastore.
- One `rule` per unique CWE; `rule.id` = the CWE string (e.g. `CWE-798`).
- Per-rule `properties."security-severity"` as a string ("8.0" HIGH / "5.0" MED /
  "2.0" LOW) — GitHub requires this to rank findings.
- Each `result` needs `locations[].physicalLocation.artifactLocation.uri`
  (relative, forward slashes) + `region.startLine`.
