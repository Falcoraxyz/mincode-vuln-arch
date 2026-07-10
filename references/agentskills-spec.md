# AgentSkills compatibility

`SKILL.md` in this repo follows the **Anthropic AgentSkills** convention so it
can be loaded by any AgentSkills-aware agent (Claude, Cline, custom loaders)
without modification.

## Required frontmatter (already satisfied)

```yaml
---
name: mincode-vuln-arch          # MUST equal the directory name
description: >-                  # short, imperative, ≤ 1024 chars
  Generate minimal, modular, human-style code ...
category: software-development
license: Apache-2.0
---
```

- `name` is kebab-case and matches the containing directory `mincode-vuln-arch`.
- `description` is present and describes *what the skill does / when to use it*.

## How an agent loads it

1. Drop (or symlink) this directory under the agent's skills root, e.g.
   `~/.claude/skills/mincode-vuln-arch/` or a project `.agents/skills/`.
2. The agent's skill loader reads `SKILL.md` frontmatter and exposes the skill
   by `name`. No packaging step needed.

## Alternative integrations (same toolkit)

| Integration | How | Best for |
|-------------|-----|----------|
| **AgentSkills** | `SKILL.md` in a skills dir | agents with a skill system |
| **MCP** | `python scripts/mcp_server.py` | Claude Desktop / Cursor / Zed / Cline native tools |
| **CLI** | `python mincode.py <cmd>` | shell-based agents / humans |
| **pip/uvx** | `pip install .` → `mincode` | global install, any agent |
| **pyz** | `python mincode.pyz <cmd>` | single-file, zero-install, air-gapped |

All five share the same scripts; the only difference is the entry point.

## Zero-dep guarantee

No `requirements.txt` / third-party imports exist. `pyproject.toml` declares
`requires-python = ">=3.8"` and no `dependencies`. `mcp_server.py` speaks the
MCP JSON-RPC protocol using only the stdlib.
