# Zero-dep config loader (`config.py`) — pattern + pitfalls

Captured from #10 (config file). Use this when you want a `mincode.toml` (or any
flat TOML) without pulling in `tomli`/`toml` as a dependency. Stdlib-only:
`tomllib` on 3.11+, a ~40-line fallback parser otherwise.

## Loader shape (condensed)
```python
import os, sys, copy

DEFAULTS = {
    "vault":  {"path": None},
    "audit":  {"skip_dirs": [], "threshold": 0},
    "llm":    {"model": None, "base_url": None},
}

def _minimal_toml(text):
    """Handles: # comments, [section], key = "str" | 123 | true/false.
    Enough for flat [section] + scalar keys (no arrays-of-tables)."""
    cfg = {"_root": {}}; cur = cfg["_root"]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line: continue
        if line.startswith("[") and line.endswith("]"):
            cur = cfg.setdefault(line[1:-1].strip(), {}); continue
        if "=" in line:
            k, v = line.split("=", 1); k = k.strip(); v = v.strip()
            if v.startswith('"') and v.endswith('"'): v = v[1:-1]
            elif v.lower() in ("true", "false"): v = v.lower() == "true"
            else:
                try: v = int(v)
                except ValueError:
                    try: v = float(v)
                    except ValueError: pass
            cur[k] = v
    return cfg

def _loads(text):
    try:
        import tomllib
        return tomllib.loads(text)
    except Exception:
        return _minimal_toml(text)

def _find_config(explicit):
    if explicit and os.path.exists(explicit): return explicit
    cands = ["mincode.toml"]
    cur = os.getcwd()
    while True:                               # walk UP from cwd
        cands.append(os.path.join(cur, "mincode.toml"))
        parent = os.path.dirname(cur)
        if parent == cur: break
        cur = parent
    home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    cands.append(os.path.join(home, "mincode.toml"))
    for c in cands:
        if os.path.exists(c): return c
    return None

def load_config(explicit=None):
    cfg = copy.deepcopy(DEFAULTS)
    path = _find_config(explicit)
    if path:
        try:
            data = _loads(open(path, encoding="utf-8").read())
            data.pop("_root", None)
            for sect, vals in data.items():
                if isinstance(vals, dict) and sect in cfg:
                    cfg[sect].update(vals)
        except Exception: pass
    return cfg
```

## Precedence (apply at call site, not in the loader)
    CLI flag  >  env var  >  mincode.toml  >  built-in DEFAULTS
The loader only supplies the `mincode.toml` layer. Each script does:
```python
model = a.model or os.environ.get("OPENAI_MODEL") or cfg["llm"].get("model") or "gpt-4o-mini"
```

## Wiring a script to use it
```python
import os, sys, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # BEFORE import config
import config
...
cfg = config.load_config(a.config)
```
This relies on the script living in the same `scripts/` dir as `config.py`.
`gen_ci.py` copies the whole `scripts/` dir into the target repo as `.mincode/`,
so the import keeps working inside CI too (relative to `.mincode/`).

## Pitfalls
- **`import re` regression:** adding a regex-using function (e.g. `hashchain.py
  diff` uses `re.compile`) to a script that didn't import `re` triggers
  `NameError: name 're' is not defined` at runtime — NOT at parse. Audit every
  new function: if it uses `re`, `json`, `subprocess`, etc., confirm the import
  line is present before committing. (`hashchain.py` shipped with this bug once.)
- **`sys.path.insert` MUST precede `import config`.** Putting the import at the
  top of the file (before the path hack) raises `ModuleNotFoundError` when the
  script is run from another cwd (exactly what CI does).
- **Walk-up guard:** the `while True` that walks up from cwd MUST terminate on
  `parent == cur` (filesystem root). Without it, an infinite loop on some setups.
- **`tomllib` is 3.11+ only.** On 3.10 or below the `import tomllib` fails and the
  `_minimal_toml` fallback runs — fine for flat scalar configs, but it does NOT
  support arrays-of-tables or dotted keys. Keep the schema flat.
- **Cross-skill path:** `vault_path()` in `hashchain.py`/`sample_repo.py` falls
  back to `config.load_config()["vault"]["path"]` AFTER the `$HERMES_HOME/.env`
  lookup, so a `[vault] path` in `mincode.toml` overrides the env default. Don't
  also hardcode the vault path in the script — let config win.
- **`.mincode` re-scan:** `config.py` itself is copied into target repos by
  `gen_ci.py`. It has no `re`/`json` dependency beyond stdlib and is harmless to
  scan, but keep it import-clean (no project-specific imports).
