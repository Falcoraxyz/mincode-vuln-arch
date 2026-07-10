# mincode-vuln-arch

Minimal-code generator + vulnerability auditor + architecture miner, with a
tamper-evident **local hash-chain knowledge vault** (Obsidian) and permanent
Hermes memory persistence.

> "Ship the least code needed. Modular. Audited. Remembered."

## What it does
1. **Scaffold** minimal, modular projects (stdlib-first, one concern per module).
2. **Audit** every project for vulnerabilities (heuristic scan + optional `bandit`). HIGH = gate blocks "done".
3. **Mine** clean architecture from real repos (human or AI-authored — judged by structure) into reusable `Template-*` notes.
4. **Hash-chain** vault notes — local, append-only, tamper-evident. No network.
5. **Persist** decisions to permanent Hermes memory.
6. **Stay alive** — cron re-verifies the chain and refreshes stale templates.

## Layout
```
mincode-vuln-arch/
  SKILL.md            # Hermes skill: full workflow
  scripts/
    proj_gen.py       # minimal project scaffold
    audit.py          # heuristic vuln audit
    sample_repo.py     # mine clean architecture from a repo
    hashchain.py       # local hash-chain for vault notes
  vault/              # Obsidian vault (hash-chained notes)
    ._chain/manifest.jsonl
```

## Install (as Hermes skill)
```bash
# symlink/junction this dir into your Hermes skills folder, e.g.:
mklink /J "%LOCALAPPDATA%\hermes\skills\software-development\mincode-vuln-arch" "D:\mincode-vuln-arch"
```
Set `OBSIDIAN_VAULT_PATH` in `%HERMES_HOME%\.env` to point at `vault/`.

## Usage
```bash
python scripts/proj_gen.py myapp --path .
python scripts/audit.py myapp
python scripts/sample_repo.py <repo_path_or_url>
python scripts/hashchain.py append "vault/Audit-myapp.md"
python scripts/hashchain.py verify
```

## Architecture decision table (optimal + stable + newest usable)
See `SKILL.md`. Stdlib-first; add deps only when required.

## License
Apache-2.0
