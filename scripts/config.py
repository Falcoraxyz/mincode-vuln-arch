#!/usr/bin/env python3
"""Shared config loader for the mincode-vuln-arch toolkit. Stdlib only.

Reads an optional `mincode.toml` so users can set thresholds / vault path /
model / skip-dirs once instead of repeating CLI flags. Precedence is:
    CLI flag  >  environment var  >  mincode.toml  >  built-in default

Searched (in order) for the file:
    1. explicit --config path (if a script passes one)
    2. ./mincode.toml  (project root, cwd)
    3. walking UP from cwd  (monorepo / nested projects)
    4. <HERMES_HOME>/mincode.toml  (global default)

Schema (all keys optional):
    [vault]
    path = "D:/mincode-vuln-arch/vault"

    [audit]
    skip_dirs = ["vendor", "build"]   # extra dirs to ignore
    threshold  = 0                     # max HIGH allowed before gate fails

    [llm]
    model    = "qwen2.5-coder:7b"
    base_url = "http://localhost:11434/v1"
"""
import os, sys

# ---- built-in defaults (mirror what each script uses today) ----
DEFAULTS = {
    "vault": {"path": None},
    "audit": {"skip_dirs": [], "threshold": 0},
    "llm": {"model": None, "base_url": None},
}

# we only need a tiny TOML subset: [section] + key = "value" / key = 123 / key = true
# use stdlib tomllib on 3.11+, else a minimal fallback parser.


def _minimal_toml(text):
    cfg = {"_root": {}}
    cur = cfg["_root"]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            sect = line[1:-1].strip()
            cur = cfg.setdefault(sect, {})
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if v.startswith('"') and v.endswith('"'):
                v = v[1:-1]
            elif v.lower() in ("true", "false"):
                v = v.lower() == "true"
            else:
                try:
                    v = int(v)
                except ValueError:
                    try:
                        v = float(v)
                    except ValueError:
                        pass
            cur[k] = v
    return cfg


def _loads(text):
    try:
        import tomllib
        return tomllib.loads(text)
    except Exception:
        return _minimal_toml(text)


def _find_config(explicit):
    if explicit:
        return explicit if os.path.exists(explicit) else None
    candidates = ["mincode.toml"]
    cur = os.getcwd()
    # walk up
    while True:
        candidates.append(os.path.join(cur, "mincode.toml"))
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    candidates.append(os.path.join(home, "mincode.toml"))
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def load_config(explicit=None):
    """Return a deep-ish merged config dict (DEFAULTS <- toml)."""
    import copy
    cfg = copy.deepcopy(DEFAULTS)
    path = _find_config(explicit)
    if path:
        try:
            with open(path, encoding="utf-8") as f:
                data = _loads(f.read())
            # drop the _root placeholder if present
            data.pop("_root", None)
            for sect, vals in data.items():
                if isinstance(vals, dict) and sect in cfg:
                    cfg[sect].update(vals)
        except Exception:
            pass
    return cfg


if __name__ == "__main__":
    import json
    print(json.dumps(load_config(), indent=2))
