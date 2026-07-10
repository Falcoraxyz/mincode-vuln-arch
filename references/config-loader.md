# `config.py` wiring in this skill — gotchas

The actual zero-dep TOML loader lives in the dedicated `stdlib-toml-config`
skill (load it for the full loader code: `tomllib` 3.11+ path + minimal fallback
parser + walk-up discovery + `CLI > env > file > default` precedence). This
file covers only the **mincode-vuln-arch-specific** traps that bit us while
wiring `config.py` into `audit.py` / `llm_review.py` / `sample_repo.py` /
`hashchain.py`.

## Pitfalls (mincode-specific)
- **`import re` regression:** adding a regex-using function (e.g. `hashchain.py
  diff` uses `re.compile`) to a script that didn't import `re` triggers
  `NameError: name 're' is not defined` at RUNTIME — not at parse. A missing
  import on a module the file didn't previously use only fails when the new
  subcommand actually runs. Guardrail: when adding a `re`/`json`/`subprocess`
  function, ADD THE IMPORT in the same edit, and RUN the new subcommand once
  before committing.
- **Shared-module import ordering:** every script that does `import config`
  MUST `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` BEFORE
  the `import config` line. Putting `import config` at the top (before the path
  hack) raises `ModuleNotFoundError` when run from another cwd — exactly what
  happens in CI (scripts copied to `.mincode/`).
- **Cross-skill vault path:** `vault_path()` in `hashchain.py` / `sample_repo.py`
  falls back to `config.load_config()["vault"]["path"]` AFTER the
  `$HERMES_HOME/.env` lookup, so a `[vault] path` in `mincode.toml` overrides
  the env default. Don't also hardcode the vault path in the script — let config
  win. (`resolve_vault` in `sample_repo.py` does this; `vault_path` in
  `hashchain.py` does too.)
- **`.mincode` re-scan:** `config.py` itself gets copied into target repos by
  `gen_ci.py`. It has only stdlib deps and no project-specific imports, so it's
  harmless to scan — but keep it import-clean.
- **Walk-up guard:** the cwd walk-up in `_find_config` MUST terminate on
  `parent == cur` (filesystem root) or it loops forever on some setups.
- **`tomllib` is 3.11+ only:** on 3.10- the `import tomllib` fails and the
  minimal parser runs. Keep the `mincode.toml` schema FLAT (scalars only, no
  arrays-of-tables) so the fallback covers it.

## Precedence applied at call site (per script)
```python
model = a.model or os.environ.get("OPENAI_MODEL") or cfg["llm"].get("model") or "gpt-4o-mini"
threshold = a.threshold if a.threshold is not None else cfg["audit"]["threshold"]
skip = list(SKIP_DIRS) + list(cfg["audit"].get("skip_dirs") or [])
```
The loader only supplies the `mincode.toml` layer; CLI flag and env var win
before it.
