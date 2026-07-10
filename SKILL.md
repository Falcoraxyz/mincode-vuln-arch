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
Use `scripts/proj_gen.py` or do it by hand. Standard skeleton:
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

### 2. Mine clean architecture from sample repos
Use `scripts/sample_repo.py <repo_path_or_url>`.
- Extracts: dir layout, module boundaries, naming, public API surface, test ratio.
- Flags "clean" only if: flat-ish modular layout, no god-files (>400 lines warning), tests present, no dead deps.
- Writes a `[[Template-<name>]]` note to vault + a reusable snippet in `docs/`.
- Human OR AI-authored both accepted — judged by structure, not author.

### 3. Vulnerability audit (gate)
Use `scripts/audit.py <project_path>`.
- Heuristic scan: hardcoded secrets, eval/exec, SQL string concat, unsafe
  deserialization, path traversal, weak crypto, shell=True, missing input
  validation, dependency pinning.
- If `bandit` installed → run it too and merge findings.
- **Dependency CVE scan (#1):** finds `requirements*.txt` / `pyproject.toml` /
  `Pipfile` / `poetry.lock`, runs `pip-audit` when available (network for the
  advisory DB), else emits a LOW "install pip-audit" notice. CVEs map to
  HIGH/MED/LOW by severity.
- **CWE tagging + grade (#2):** every finding carries a CWE id (CWE-78,
  CWE-502, …); the project gets an A–F grade from a severity-weighted penalty
  (HIGH=10, MED=3, LOW=1). Grade prints with the CWE set for triage.
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

### 4b. Vault MOC (Map of Content) — #7
Use `scripts/vault_index.py [--vault <dir>]`.
- Scans all `.md` notes, groups by prefix: `Audit-*` (Audits), `Template-*`
  (Architecture Templates), `Common-*` (Cross-Project Learnings), rest → Notes.
- Emits `Index.md` with Obsidian `[[wikilinks]]` + per-note CWE tags.
- Auto cross-links notes sharing ≥1 CWE in a "Related by CWE" section.
- Idempotent — rerun after every append to keep the vault navigable in Obsidian.
- Regenerate MOC as part of the post-audit / post-mine workflow.

### 5. Persist to permanent memory
- Save durable facts/decisions to Hermes memory (architecture choices, gotchas,
  user prefs). NOT task progress. Use the `memory` tool.
- Vault is the long-term KB; memory is the cross-session shortcut.

### 6. Keep the vault alive (cron, optional)
Schedule `hashchain.py verify` + `audit.py` + `sample_repo.py` rescan on a cron
so the KB self-heals and grows. Recommend daily/weekly.

## Architecture Decision table (optimal+stable+newest usable)
| Stack | Pick | Why |
|-------|------|-----|
| CLI / small tool | stdlib + argparse, single `main()` entry, modules by verb | zero deps, minimal |
| Web API | FastAPI (async, typed) OR stdlib `http.server` if tiny | FastAPI stable+modern; stdlib if no dep wanted |
| Data / ETL | Python modules + pydantic for schema | typed, minimal boilerplate |
| Frontend | Vite + vanilla TS or Svelte (no React overhead) if small | lightest modern |
| Long-running svc | supervisor/process per concern, config via env | simple, observable |
| Storage | SQLite (single file) unless scale demands Postgres | zero-ops, durable |
Update this table as stacks evolve. Prefer newest only if it is stable + usable.

## Pitfalls
- Don't mine a repo that isn't clean — garbage in, garbage template.
- Hash-chain is local tamper-evidence, NOT a distributed ledger. No network.
- Audit is heuristic — a clean scan is not a guarantee. State residual risk.
- Minimal ≠ untested. Every module gets at least one test.
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
