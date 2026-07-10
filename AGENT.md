# AGENT.md — mincode-vuln-arch quick reference (drop into any repo)

A minimal, dependency-free toolkit to **generate minimal code**, **audit for
vulnerabilities**, **mine clean architecture**, and **persist findings in a
tamper-evident hash-chain vault**. This file is a copy-paste cheat-sheet so any
AI agent (Claude, Cline, Cursor, Zed, Codex, Hermes, …) or human can wire the
audit gate into a project in one step.

## 1. Install (pick one)

```bash
# A. Clone (dev / full)
git clone https://github.com/Falcoraxyz/mincode-vuln-arch
export OBSIDIAN_VAULT_PATH="$PWD/vault"   # optional

# B. Pip-installable (global `mincode` command)
pip install .            # or: uv pip install .   /   uvx --from . mincode

# C. Single file (zero-install, shareable, any Python 3.8+)
python build_pyz.py && python mincode.pyz audit . --no-vault

# D. MCP server (native tool for Claude Desktop / Cursor / Zed / Cline)
python scripts/mcp_server.py
# client config:
# { "mcpServers": { "mincode": { "command": "python",
#   "args": ["/path/to/mincode-vuln-arch/scripts/mcp_server.py"] } } }
```

## 2. Enable the audit gate (one command)

```bash
python mincode.py init .          # writes mincode.toml + .github/workflows/audit.yml
# or, installable:  mincode init .
# or, pyz:          python mincode.pyz init .
```

This scaffolds `mincode.toml` and a CI workflow that runs
`mincode audit . --sarif audit.sarif` and **fails on HIGH findings**.

## 3. Per-change loop (run before marking "done")

```bash
python mincode.py audit . --no-vault     # HIGH findings block "done"
python mincode.py tests .                # generate + run typed smoke tests
python mincode.py llm . --no-vault       # logic-flaw review (skips if no backend)
```

Optional vault persistence (for cross-session memory):
```bash
export OBSIDIAN_VAULT_PATH="$PWD/vault"
python mincode.py audit .                # writes Audit-<name>-<date>.md
python mincode.py mine <repo_url>        # writes Template-<name>.md
python mincode.py vault verify           # tamper-evident check
```

## 4. Commands

| Command | Maps to | Purpose |
|---------|---------|---------|
| `mincode gen <p>` | `proj_gen.py` | scaffold minimal project (auto git + tag) |
| `mincode tests <p>` | `gen_tests.py` | generate typed smoke tests |
| `mincode audit <p>` | `audit.py` | vuln audit + graded CI gate |
| `mincode mine <repo>` | `sample_repo.py` | mine clean architecture patterns |
| `mincode llm <p>` | `llm_review.py` | LLM logic-flaw review (local-first) |
| `mincode vault <cmd>` | `hashchain.py` | append / verify / diff / status |
| `mincode moc` | `vault_index.py` | rebuild Obsidian MOC |
| `mincode learn` | `cross_learn.py` | aggregate recurring CWE |
| `mincode ci <repo>` | `gen_ci.py` | generate CI gate workflow |
| `mincode init <repo>` | — | scaffold `mincode.toml` + CI into a repo |
| `mincode mcp` | `mcp_server.py` | start MCP server (stdio) |

All extra args pass through (`--vault`, `--no-vault`, `--sarif`, `--threshold`, …).

## 5. Config (`mincode.toml`)

```toml
[vault]
path = "path/to/vault"          # optional; default ./mincode-vault

[audit]
skip_dirs = ["vendor", "build"] # extra dirs to skip
threshold  = 0                  # max HIGH allowed before gate fails (0 = zero-tolerance)

[llm]
model   = "gpt-4o-mini"         # or local: the server auto-detects Ollama/llama.cpp
base_url = "http://localhost:11434/v1"
```

Precedence: CLI flag > env var > `mincode.toml` > default.

## 6. Portability notes

- **No hardcoded paths.** Vault defaults to `./mincode-vault` when
  `OBSIDIAN_VAULT_PATH` / `--vault` / `mincode.toml` are unset.
- **Zero external dependencies.** Pure Python stdlib; runs on any OS with 3.8+.
- **AgentSkills-compatible** `SKILL.md` (frontmatter `name` = dir name) so
  AgentSkills-aware loaders pick it up directly.
- **MCP + CLI + pyz + pip** — same toolkit, four ways to call it.

## 7. CWE categories caught (heuristic, multi-language)

`CWE-78/77` command injection · `CWE-89/564` SQLi · `CWE-79` XSS ·
`CWE-502` unsafe deserialization · `CWE-22/23` path traversal ·
`CWE-798/259` hardcoded secrets · `CWE-295/327` weak crypto ·
`CWE-94/95` eval/exec · `CWE-502/73` temp-file injection ·
`CWE-319` cleartext transmission · `CWE-327` ECB/null IV.

> Audit is heuristic — a clean scan is not a guarantee. Use `llm_review` for
> logic blind spots when a model endpoint is available.
