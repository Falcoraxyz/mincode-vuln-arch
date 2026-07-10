# 🐦 mincode-vuln-arch

> **Ship the least code needed. Modular. Audited. Remembered.**

A self-contained toolkit + Hermes skill that generates **minimal, modular,
human-style code from scratch**, **audits every project** for vulnerabilities,
**mines clean architecture** from real repos into reusable templates, and
**persists everything** into a tamper-evident **local hash-chain Obsidian vault**
plus permanent Hermes memory.

Zero external runtime dependencies — everything runs on the Python standard
library (optional `bandit` / `pip-audit` / an LLM key deepen coverage).

[![License: Apache-2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org)
[![Hermes Skill](https://img.shields.io/badge/Hermes-skill-green.svg)](https://hermes-agent.nousresearch.com)

---

## ✨ Features

| # | Capability | Script | What it does |
|---|-----------|--------|--------------|
| 1 | **Scaffold** | `proj_gen.py` | Minimal modular skeleton (`src/ tests/ docs/`), stdlib-first. Auto `git init` + `scaffold-<date>` tag. |
| 2 | **Audit** | `audit.py` | Heuristic vuln scan + optional `bandit`. CWE-tagged, A–F grade, dependency CVE scan (`pip-audit`). |
| 2b | **SARIF export** | `audit.py` | `--sarif out.sarif` (2.1.0) for GitHub code scanning; auto-uploaded by the CI gate. |
| 2d | **HTML report** | `audit.py` | `--report out.html` (self-contained: severity colors, CWE links, grade badge). Uploaded by CI. |
| 3 | **Mine architecture** | `sample_repo.py` | Extract clean module boundaries + reusable code snippets from any repo (human or AI-authored). |
| 3b | **Multi-language audit** | `audit.py` | Heuristic scan across Python + JS/TS/Go/Rust/sh (polyglot rules), CWE-tagged. |
| 3c | **Arch auto-apply** | `sample_repo.py` | `--apply-arch` appends missing Architecture Decision rows to SKILL.md (#9). |
| 4 | **Gen tests** | `gen_tests.py` | `ast`-based test generation — typed dummy args + `isinstance` assertions from return annotations (#8). Zero-dep `unittest`. |
| 5 | **Hash-chain vault** | `hashchain.py` | Local, append-only, **HMAC-signed** notes — tamper-evident + forged-resistant. No network. |
| 6 | **Vault MOC** | `vault_index.py` | Auto-generated Obsidian Map of Content with `[[wikilinks]]` + CWE cross-links. |
| 7 | **Cross-project learn** | `cross_learn.py` | Aggregates recurring CWEs → `Common-Mistakes.md` + CI guardrail suggestions. |
| 8 | **LLM review** | `llm_review.py` | Logic-flaw review via OpenAI-compatible API; auto-detects Ollama/llama.cpp (offline) or OpenAI. No key → safe skip. |
| 9 | **Living arch table** | `sample_repo.py` | Detects stacks in mined repos; flags missing rows in the SKILL.md decision table. |
| 10 | **Auto-git** | `proj_gen.py` / `audit.py` | Tags `scaffold-<date>` / `audit-clean-<date>` — every green state is versioned. |
| 12 | **Config file** | `config.py` | Optional `mincode.toml` for vault path, audit skip-dirs/threshold, LLM model/base_url. |

---

## 📂 Layout

```
mincode-vuln-arch/
├── SKILL.md                 # Hermes skill: full workflow + architecture decision table
├── README.md
├── LICENSE                  # Apache-2.0
├── references/              # deep-dive docs (audit, tests, windows ops, gotchas)
├── scripts/
│   ├── proj_gen.py          # minimal project scaffold (auto-git)
│   ├── audit.py             # vuln audit (CWE + A-F grade + dep CVE)
│   ├── sample_repo.py       # mine clean architecture + snippets + arch suggestions
│   ├── gen_tests.py         # smoke-test generation (ast, zero-dep)
│   ├── hashchain.py         # HMAC-signed local hash-chain
│   ├── vault_index.py       # Obsidian MOC / wikilink index
│   ├── cross_learn.py      # cross-project CWE aggregation
│   ├── llm_review.py        # LLM-assisted logic-flaw review
│   └── gen_ci.py           # generate GitHub Actions audit-gate (#1)
└── vault/                   # Obsidian vault (hash-chained notes)
    ├── ._chain/manifest.jsonl   # hash-chain ledger (HMAC key gitignored)
    ├── Index.md             # auto-generated Map of Content
    └── Audit-*, Template-*  # hand-authored knowledge notes
```

---

## 🚀 Quick start

### As a Hermes skill
```bash
# Junction this repo into your Hermes skills folder (Windows example):
cmd /c mklink /J "%LOCALAPPDATA%\hermes\skills\software-development\mincode-vuln-arch" "D:\mincode-vuln-arch"

# Point Hermes at the vault (in %HERMES_HOME%\.env):
OBSIDIAN_VAULT_PATH=D:/mincode-vuln-arch/vault
```
Then: `skill_view(name='mincode-vuln-arch')` — or just say *"use mincode-vuln-arch for X"*.

### Standalone
```bash
git clone https://github.com/Falcoraxyz/mincode-vuln-arch
export OBSIDIAN_VAULT_PATH="$PWD/vault"   # optional, for vault output
```

---

## 🔧 Usage

```bash
# 1. Scaffold a minimal modular project (auto git + tag)
python scripts/proj_gen.py myapp --path .

# 2. Generate smoke tests from src/ (zero-dep unittest)
python scripts/gen_tests.py myapp

# 3. Audit for vulnerabilities (HIGH blocks "done")
python scripts/audit.py myapp

# 4. Mine clean architecture from any repo (URL or local path)
python scripts/sample_repo.py <repo_url_or_path>

# 5. Optional: LLM review for logic flaws (needs OPENAI_API_KEY)
python scripts/llm_review.py myapp

# 5b. Generate CI gate (fails on any HIGH finding)
python scripts/gen_ci.py --path myapp

# 6. Persist + harden the knowledge vault
python scripts/hashchain.py append "vault/Audit-myapp.md"
python scripts/hashchain.py verify
python scripts/vault_index.py --vault vault     # regenerate MOC
python scripts/cross_learn.py --vault vault     # aggregate recurring CWE
```

### Example audit output
```
AUDIT demo — 1 HIGH, 2 MED, 1 LOW
  HIGH  CWE-78  shell=True in src/cli.py:42        (eval/exec)
  MED   CWE-89  SQL string concat in src/db.py:17  (SQLi)
  MED   CWE-502 unsafe yaml.load in src/cfg.py:9    (deserialization)
  LOW   CWE-798 hardcoded API key in src/secret.py:3
GRADE: D  (penalty 36)   CWEs: {CWE-78, CWE-89, CWE-502, CWE-798}
```

---

## 🧠 How it works

```
   code ──► proj_gen ──► gen_tests ──► audit ──► (llm_review)
                                    │
            sample_repo ◄── clean repos (human or AI)
                                    │
                          ┌─────────┴──────────┐
                     hashchain.py          vault_index.py
                  (HMAC-signed ledger)    (Obsidian MOC)
                          │                    │
                     cross_learn.py ◄──────────┘
                  (Common-Mistakes.md, guardrails)
                          │
                   Hermes memory (permanent)
```

The vault is a **local hash-chain** — each note links to the previous note's
hash and is **HMAC-signed** with a per-vault key. Editing a note *or* the ledger
together is caught on `verify`. This is tamper-evident + forged-resistant, **not**
a distributed ledger — no network required.

---

## 🏗️ Architecture decision table

The skill picks the **optimal + stable + newest usable** stack per concern.
Full table lives in [`SKILL.md`](SKILL.md). `sample_repo.py` checks mined repos
against it and suggests new rows (see *Living arch table* above).

| Stack | Pick |
|-------|------|
| CLI | stdlib + argparse/click |
| Web API | FastAPI (or stdlib `http.server` if tiny) |
| Data / ETL | Python modules + pydantic |
| Frontend | Vite + vanilla TS / Svelte |
| Long-running svc | supervisor, config via env |
| Storage | SQLite (Postgres only if scale demands) |

---

## 📌 Notes & limits

- Audit is **heuristic** — a clean scan is not a guarantee. `llm_review.py`
  covers logic blind spots when a key is available.
- `pip-audit` (dep CVEs) and `bandit` are optional install/network extras.
- The hash-chain is **local** tamper-evidence, not a blockchain. Never commit
  the HMAC key (`vault/._chain/.key` is gitignored).
- Run generated tests with `python tests/<mod>_test.py` (reliable on Windows;
  `unittest discover` can report 0 in some envs).

---

## 📄 License

[Apache-2.0](LICENSE) © Falcoraxyz
