# ROADMAP — mincode-vuln-arch

All 10 original improvement ideas shipped + 6 extra. Status snapshot.

## Original 10 ideas (all done)
| # | Idea | Script | Status |
|---|------|--------|--------|
| 1 | HMAC-signed hash chain | `hashchain.py` | ✅ |
| 2 | CWE-tagged + A–F grade | `audit.py` | ✅ |
| 3 | Dependency CVE scan | `audit.py` (pip-audit) | ✅ |
| 4 | Snippet extraction | `sample_repo.py` | ✅ |
| 5 | Test generation (assertion-aware) | `gen_tests.py` | ✅ |
| 6 | Cross-project learnings | `cross_learn.py` | ✅ |
| 7 | Obsidian MOC | `vault_index.py` | ✅ |
| 8 | Living architecture table | `sample_repo.py` | ✅ |
| 9 | LLM review | `llm_review.py` | ✅ |
| 10 | Auto-git tags | `proj_gen.py` / `audit.py` | ✅ |

## Extra ideas added mid-stream (all done)
| # | Idea | Script | Status |
|---|------|--------|--------|
| 1 | CI gate (GitHub Actions) | `gen_ci.py` | ✅ |
| 2 | Test execution gate | `audit.py` (`--run-tests`) | ✅ |
| 3 | Multi-language audit | `audit.py` (polyglot) | ✅ |
| 4 | SARIF export | `audit.py` (`--sarif`) | ✅ |
| 5 | Local LLM auto-detect | `llm_review.py` | ✅ |
| 6 | Vault regression diff | `hashchain.py` (`diff`) | ✅ |
| 7 | HTML report | `audit.py` (`--report`) | ✅ |
| 8 | Assertion-aware tests | `gen_tests.py` | ✅ |
| 9 | Arch auto-apply | `sample_repo.py` (`--apply-arch`) | ✅ |
| 10 | Config file | `config.py` + `mincode.toml` | ✅ |

## Portability track (agent-agnostic) — all done
| # | Idea | Deliverable | Status |
|---|------|-------------|--------|
| 1 | Vault optional | `--no-vault` in `llm_review.py`/`sample_repo.py`, default `./mincode-vault` | ✅ |
| 2 | Single CLI `mincode` | `mincode.py` dispatcher + `scripts/cli.py` | ✅ |
| 3 | AgentSkills spec | `SKILL.md` frontmatter + `references/agentskills-spec.md` | ✅ |
| 4 | Path hardening | no hardcoded `D:/`, stdlib-only config loader | ✅ |
| 5 | Zipapp single-file | `build_pyz.py` → `mincode.pyz` | ✅ |
| 6 | Pip-installable | `pyproject.toml` (`mincode_vuln_arch` + `mincode` console script) | ✅ |
| 7 | MCP server | `scripts/mcp_server.py` (zero-dep stdio JSON-RPC) | ✅ |
| 8 | Docker image | *(optional — see notes)* | ⬜ |
| 9 | `mincode init` | one-shot `mincode.toml` + CI scaffold | ✅ |
| 10 | AGENT.md cheat-sheet | `AGENT.md` drop-in quick reference | ✅ |

> The toolkit is now **fully portable**: AgentSkills, MCP, CLI, pip/uvx, and pyz
> all wrap the same scripts. No Hermes or Obsidian required to run.

- [ ] **Dashboard**: aggregate grade trend across all audited projects
