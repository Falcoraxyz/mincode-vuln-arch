---
name: mincode-vuln-arch
description: >
  Generate minimal, modular, human-style code from scratch; audit every
  project for vulnerabilities; mine clean architecture patterns from real
  repos (human or AI-authored) as reusable templates; persist results into a
  tamper-evident hash-chain Obsidian vault + permanent Hermes memory. Picks
  the optimal/stable/newest usable architecture per stack.
category: software-development
---

# Minimal Code + Vuln Audit + Architecture Mining → Hash-Chain Vault

Goal: ship the *least* code needed, modular, from zero. Every project gets a
vulnerability audit. Real repos (human or AI-built, as long as structure is
clean) become reusable architecture templates. Final output hardens a permanent
knowledge base (Obsidian hash-chain vault) + Hermes memory. Architecture chosen
= most optimal / stable / newest that is actually usable for the stack.

## Non-negotiables
- Minimal: no code beyond what the requirement demands. No premature abstraction.
- Modular: one responsibility per module/file. Clear public interface.
- Audit every project before declaring done (vuln gate).
- Output lands in vault as append-only hash-chained notes (tamper-evident, local, no network).

## Workflow (run in order)

### 0. Resolve environment
- Vault: `${OBSIDIAN_VAULT_PATH}` from `$HERMES_HOME/.env`, else `~/Documents/Obsidian Vault`.
- Tools: `python` (3.11+ ok). `bandit` optional (pip) for deeper Python audit.
- Scripts live in this skill's `scripts/` dir. Pass absolute paths.

### 1. Scaffold minimal modular project
Use `scripts/proj_gen.py <name> [--path .] [--no-git]`. Standard skeleton:
```
<project>/
  src/            # one module per concern, thin public API
  tests/          # one test file per module
  docs/           # architecture.md + decisions
  .ok/            # (optional) OpenKnowledge artifacts
  README.md
  CHANGELOG.md    # hash-chain anchored
```
- Pick architecture per stack from the **Architecture Decision** table below.
- Do NOT add frameworks/libs unless required. Stdlib-first.
- **Auto-git (#6):** `proj_gen.py` runs `git init` + initial commit and tags
  `scaffold-<date>` (skip with `--no-git`). `audit.py` tags `audit-clean-<date>`
  on a fully clean pass — every green state is versioned.
- **CI gate (#1):** `scripts/gen_ci.py --path <repo>` writes
  `.github/workflows/audit.yml` + copies scripts to `.mincode/` so the audit is
  *enforced* in CI (fails on any HIGH). See `references/ci-gate.md`.

### 2. Mine clean architecture from sample repos
Use `scripts/sample_repo.py <repo_path_or_url>`.
- Extracts: dir layout, module boundaries, naming, public API surface, test ratio.
- Flags "clean" only if: flat-ish modular layout, no god-files (>400 lines warning), tests present, no dead deps.
- Writes a `[[Template-<name>]]` note to vault + a reusable snippet in `docs/`.
- **Snippet extraction (#4):** also pulls public function/class signatures from
  clean `.py` modules into a `## Reusable snippets` section (vault note) and a
  local `docs/snippets.md` — reusable code patterns, not just structure stats.
- Human OR AI-authored both accepted — judged by structure, not author.

### 3. Vulnerability audit (gate)
Use `scripts/audit.py <project_path>`.
- Heuristic scan: hardcoded secrets, eval/exec, SQL string concat, unsafe
  deserialization, path traversal, weak crypto, shell=True, missing input
  validation, dependency pinning. **Multi-language (#3):** `.py` uses Python-specific
  rules; `.js/.jsx/.ts/.tsx/.go/.rs/.sh` use polyglot rules (child_process exec,
  `new Function`, SQL concat, hardcoded secrets, weak hash, TLS-skip). `.json/.yaml`
  scanned for secrets only.
- If `bandit` installed → run it too and merge findings.
- **Dependency CVE scan (#1):** finds `requirements*.txt` / `pyproject.toml` /
  `Pipfile` / `poetry.lock`, runs `pip-audit` when available (network for the
  advisory DB), else emits a LOW "install pip-audit" notice. CVEs map to
  HIGH/MED/LOW by severity.
- **CWE tagging + grade (#2):** every finding carries a CWE id (CWE-78,
  CWE-502, …); the project gets an A–F grade from a severity-weighted penalty
  (HIGH=10, MED=3, LOW=1). Grade prints with the CWE set for triage.
- **Test generation (#5):** `scripts/gen_tests.py <project>` parses `src/` with
  `ast` (stdlib) and writes one smoke test per public function/class into
  `tests/<module>_test.py` (skips existing). Default framework `unittest`
  (stdlib, zero-dep) — run each with `python tests/<module>_test.py` or
  `python -m unittest discover -s tests` from the project root. Fills the
  "minimal ≠ untested" gap: every module gets at least a smoke test.
- Severity: HIGH / MED / LOW. Project blocked from "done" if any HIGH unresolved.
- Writes `[[Audit-<project>-<date>]]` to vault.

### 4. Hash-chain the vault notes
Use `scripts/hashchain.py append <vault_note_path>`.
- Computes sha256 of note body, links to previous note hash in chain manifest
  `<vault>/._chain/manifest.jsonl` (append-only, tamper-evident).
- **HMAC signing (#3):** each entry is signed with a local key
  `<vault>/._chain/.key` (auto-generated, 32 bytes). Verify checks both the
  hash linkage AND the HMAC, so editing the manifest + note together is caught
  (forged-resistant, not just tamper-evident). Key is per-vault; rotate with
  `hashchain.py rotate-key`.
- Each note gets frontmatter: `chain_prev`, `chain_hash`, `chain_ts`.
- Commands: `append`, `verify`, `status`, `rotate-key`.
- Verification: `hashchain.py verify` replays manifest, fails on any mismatch or
  signature error.
- **Re-append rule:** if a note was already chained and you edit it, you MUST
  re-run `append` — it strips the stale frontmatter and re-signs the clean body.
  Skipping this leaves a false TAMPER at #1 on `verify`. (See
  `references/audit-and-chain.md`.)

### 4b. Vault MOC (Map of Content) — #7
Use `scripts/vault_index.py [--vault <dir>]`.
- Scans all `.md` notes, groups by prefix: `Audit-*` (Audits), `Template-*`
  (Architecture Templates), `Common-*` (Cross-Project Learnings), rest → Notes.
- Emits `Index.md` with Obsidian `[[wikilinks]]` + per-note CWE tags.
- Auto cross-links notes sharing ≥1 CWE in a "Related by CWE" section.
- Idempotent — rerun after every append to keep the vault navigable in Obsidian.
- Regenerate MOC as part of the post-audit / post-mine workflow.

### 5b. Cross-project learnings — #8
Use `scripts/cross_learn.py [--vault <dir>]`.
- Scans all `Audit-*` / `Template-*` notes, extracts CWE tags, builds a
  frequency map of recurring weaknesses across projects.
- Writes `Common-Mistakes.md`: ranked CWE table + per-CWE mitigation hints +
  "Suggested guardrails" (CWEs seen in ≥2 projects = systemic → add to CI gate).
- The MOC auto-links it under "Cross-Project Learnings", so the KB self-improves
  as more audits land. Rerun after every audit.

### 5c. LLM-assisted code review — #9
Use `scripts/llm_review.py <project> [--model <name>]`.
- Sends source files (excludes `tests/`) to an OpenAI-compatible chat endpoint
  and asks the model to flag logic bugs / authz / TOCTOU / injection-via-data /
  dead code that the heuristic audit cannot catch.
- Requires `OPENAI_API_KEY` (optional `OPENAI_BASE_URL`, `OPENAI_MODEL`); if unset
  it prints a notice and exits 0 — the heuristic audit still applies. Stdlib only
  (urllib), no SDK dependency.
- Writes `[[Audit-<project>-llm-<date>]]` to the vault. Use after `audit.py` to
  cover the blind spots regex misses. Network + key needed; not for offline use.

### 2b. Living architecture table — #10
`sample_repo.py` now auto-detects stacks in a mined repo (CLI, Web API, FastAPI,
SQLite, Frontend, Data/ETL, Storage, Long-running svc) and compares them against
the **Architecture Decision table** in this SKILL.md.
- If a detected stack has no table row, the `Template-*` note gets an
  `## Arch suggestions (#10)` block: "UPDATE SKILL.md: missing rows for: …".
- Add the missing row so future scaffolds pick the optimal/stable/newest stack.
  The table is a living doc — evolve it as stacks change.

## Gotchas
Operational lessons — full detail in `references/gotchas.md`:
- Chain ONLY hand-authored notes (`Audit-*`/`Template-*`). `vault_index.py` and
  `cross_learn.py` outputs (`Index.md`, `Common-Mistakes.md`) are auto-generated —
  regenerate them AFTER chaining, never append them (false TAMPER on verify).
- Run generated tests with `python tests/<mod>_test.py` (unittest discover returns
  0 in this Windows env).
- To relocate the skill: directory-junction the Hermes skill dir to this repo via
  `cmd /c mklink /J` (bash `cmd //c` strips quotes and fails silently).
- **Deployment gotchas** (Windows junction relocation, cross-drive relpath, unittest
  direct-run, hashchain re-sign frontmatter): see `references/windows-deployment.md`.
- **CI gate generator (`gen_ci.py`, #1):** writes `.github/workflows/audit.yml`
  that runs `gen_tests.py` → smoke tests → `audit.py` (fails on any HIGH). It
  also copies `scripts/` into the target repo as `.mincode/`. GOTCHAS:
  - `.mincode/` MUST be committed — do NOT gitignore it (CI needs the scripts).
  - The generated YAML must use RELATIVE paths only (`.mincode/...`); never
    embed absolute Windows paths — they break Linux CI runners.
  - `python -m unittest discover -s tests` can pass vacuously (0 tests) in some
    envs; the audit gate is the real enforcement. See `references/ci-gate.md`.
- Save durable facts/decisions to Hermes memory (architecture choices, gotchas,
  user prefs). NOT task progress. Use the `memory` tool.
- Vault is the long-term KB; memory is the cross-session shortcut.

### 6. Keep the vault alive (cron, optional)
Schedule `hashchain.py verify` + `audit.py` + `sample_repo.py` rescan on a cron
so the KB self-heals and grows. Recommend daily/weekly.

## Architecture Decision table (optimal+stable+newest usable)
| Stack | Pick | Why |
|-------|------|-----|
| CLI | stdlib + argparse/click, single `main()` entry, modules by verb | zero deps, minimal |
| Web API | FastAPI (async, typed) OR stdlib `http.server` if tiny | FastAPI stable+modern; stdlib if no dep wanted |
| Data / ETL | Python modules + pydantic for schema | typed, minimal boilerplate |
| Frontend | Vite + vanilla TS or Svelte (no React overhead) if small | lightest modern |
| Long-running svc | supervisor/process per concern, config via env | simple, observable |
| Storage | SQLite (single file) unless scale demands Postgres | zero-ops, durable |
Update this table as stacks evolve. Prefer newest only if it is stable + usable.

## Pitfalls
- Don't mine a repo that isn't clean — garbage in, garbage template.
- Hash-chain is local tamper-evidence + HMAC-signed (forged-resistant), NOT a
  distributed ledger. No network. Key is per-vault at `vault/._chain/.key`
  (gitignored — never commit it).
- Audit is heuristic — a clean scan is not a guarantee. State residual risk.
  `pip-audit` (for dep CVEs) and `bandit` are optional network/install extras.
- Minimal ≠ untested. `gen_tests.py` gives every module a smoke test.
- **Re-appending an already-chained note:** `hashchain append` strips any
  existing frontmatter, re-signs the clean body, and rewrites fresh
  frontmatter. Never hand-edit a note's `chain_*` frontmatter — it triggers a
  false TAMPER on `verify`. If a note body changed outside `append`, rebuild the
  chain from a clean state: `rm -rf vault/._chain` then re-`append` notes in
  order. (Editing the manifest AND the note together is caught by HMAC — that
  is the intended forge detection, not a bug.)
- **Cross-drive vault (Windows C:↔D:):** `hashchain` uses `os.path.relpath`
  but falls back to the absolute path when the note and vault are on different
  mounts (ValueError). Always set `OBSIDIAN_VAULT_PATH` to the real vault dir;
  junction/symlink the skill dir from Hermes to the D: repo if you want one
  source of truth (use `subprocess.run('mklink /J ...', shell=True)` in Python
  — raw `cmd /c mklink` strips quotes and fails under git-bash).
- **Running generated tests:** prefer `python tests/<mod>_test.py` (reliable,
  uses `unittest.main`). `python -m unittest discover -s tests` can report 0
  tests in some envs due to loader path quirks — fall back to the direct file
  run or `python -m unittest tests.<mod>_test`. See `references/test-generation.md`.
- **Living arch table (#10) label contract:** `sample_repo.py`'s
  `detect_stack_hints()` keys MUST equal the Architecture Decision table row
  names below EXACTLY. They currently drifted (`FastAPI`, `SQLite`, `Data/ETL`
  in the script vs `Web API`, `Storage`, `Data / ETL` in the table) which made
  mined repos false-flag "UPDATE SKILL.md" when no update was needed. If a repo
  is flagged missing but the stack is already covered, FIX THE SCRIPT'S marker
  KEY to match the table row — do NOT add a duplicate table row to silence it.
  Keep one canonical row name per stack.
- On Windows the skill dir (C:) and vault (D:) are on different drives —
  scripts use `_rel_or_abs` for cross-drive paths. See
  `references/windows-operations.md` for junction creation + consent-gate gotchas.
- Never bundle `rm -rf` with other steps in one terminal call — Hermes consent
  gate blocks it. Split into separate calls.

## Verification
- `proj_gen.py` output builds/runs.
- `audit.py` exits 0 with no HIGH.
- `hashchain.py verify` returns OK.
- Vault note links render; memory entry present.

## References
- `references/audit-and-chain.md` — audit regex gotchas, hash-chain design, and the vault env-var resolution rule. Read before touching the scanners.
- `references/windows-operations.md` — cross-drive relpath, junction creation via subprocess, consent-gate split. Read before any Windows path/move work.
- `references/test-generation.md` — why `discover` reports 0 tests, the `__file__`-relative sys.path insert, and `__main__.py` skip. Read before touching gen_tests.py.
