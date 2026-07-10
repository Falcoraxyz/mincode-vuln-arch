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

## Possible next ideas (not started)
- [ ] **HTML report → Obsidian publish** or Markdown digest in vault
- [ ] **`mincode.toml` schema validation** + example committed to repo
- [ ] **PR bot**: comment SARIF/HTML summary on GitHub PRs
- [ ] **Semgrep/trivy adapter** (optional, behind env flag) for deeper coverage
- [ ] **Vault sync** (git-backed) for multi-machine teams
- [ ] **Per-language test generation** (JS/Go/Rust) in `gen_tests.py`
- [ ] **Arch table → scaffold template** auto-injection in `proj_gen.py`
- [ ] **Dashboard**: aggregate grade trend across all audited projects
