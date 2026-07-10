#!/usr/bin/env python3
"""Mine clean architecture patterns from a repo (local path or git URL).
Usage: python sample_repo.py <repo_path_or_url> [--vault <dir>]

Judges by STRUCTURE only (human or AI-authored both fine):
 - modular layout (per-concern dirs)
 - no god-files (>400 lines flagged)
 - tests present
 - no obvious dead deps
Writes [[Template-<name>]] note to vault + prints a reusable snippet.
"""
import os, sys, subprocess, argparse, json, datetime, ast, re

SKIP = (".git", "node_modules", "__pycache__", ".ok", "venv", ".venv", "dist", "build")
GOD_LINES = 400
MAX_SNIPPETS_PER_MOD = 4


def resolve_vault(explicit):
    """Read OBSIDIAN_VAULT_PATH from $HERMES_HOME/.env (consistent with hashchain.py),
    then os.environ, then default. Do NOT rely on os.environ alone."""
    if explicit:
        return explicit
    env = os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), ".env")
    try:
        with open(env) as f:
            for line in f:
                if line.startswith("OBSIDIAN_VAULT_PATH="):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return os.environ.get("OBSIDIAN_VAULT_PATH") or os.path.expanduser("~/Documents/Obsidian Vault")


def clone_or_use(target):
    if os.path.exists(target):
        return target, False
    tmp = os.path.join(os.path.dirname(os.path.abspath(target)) or ".",
                       "_sample_" + os.path.basename(target))
    subprocess.run(["git", "clone", "--depth", "1", target, tmp], check=True)
    return tmp, True


def analyze(path):
    dirs, files, god = {}, [], []
    test_files = 0
    for dp, dn, fn in os.walk(path):
        if any(s in dp.split(os.sep) for s in SKIP):
            continue
        for name in fn:
            fp = os.path.join(dp, name)
            rel = os.path.relpath(fp, path)
            files.append(rel)
            if "test" in name.lower():
                test_files += 1
            if name.endswith((".py", ".js", ".ts")):
                try:
                    n = sum(1 for _ in open(fp, errors="ignore"))
                    if n > GOD_LINES:
                        god.append((rel, n))
                except Exception:
                    pass
    # top-level dirs = module boundaries
    for d in sorted(os.listdir(path)):
        fd = os.path.join(path, d)
        if os.path.isdir(fd) and d not in SKIP:
            dirs[d] = len([x for x in files if x.startswith(d + os.sep)])
    return {"dirs": dirs, "n_files": len(files), "tests": test_files,
            "god_files": god}


def extract_snippets(path):
    """Pull short public function/class signatures from clean .py modules.
    Returns list of (file, signature)."""
    out = []
    for dp, dn, fn in os.walk(path):
        if any(s in dp.split(os.sep) for s in SKIP):
            continue
        for name in fn:
            if (not name.endswith(".py") or name in ("__init__.py", "__main__.py")
                    or "test" in name.lower()):
                continue
            fp = os.path.join(dp, name)
            rel = os.path.relpath(fp, path)
            try:
                src = open(fp, encoding="utf-8").read()
                tree = ast.parse(src)
            except Exception:
                continue
            got = 0
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and not node.name.startswith("_"):
                    sig = f"def {node.name}(" + ", ".join(a.arg for a in node.args.args) + ")"
                    out.append((rel, sig))
                    got += 1
                elif isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                    bases = ", ".join(getattr(b, "id", getattr(b, "attr", "")) for b in node.bases)
                    out.append((rel, f"class {node.name}({bases})"))
                    got += 1
                if got >= MAX_SNIPPETS_PER_MOD:
                    break
    return out


def detect_stack_hints(path):
    """Best-effort stack detection from filenames + dep manifests."""
    hints = set()
    markers = {
        "FastAPI": ("fastapi", "main.py", "app.py"),
        "Web API": ("routes", "views", "controller"),
        "CLI": ("__main__.py", "argparse", "click"),
        "SQLite": ("sqlite", ".db", ".sqlite"),
        "Data/ETL": ("pandas", "etl", "transform"),
        "Frontend": ("vite", "svelte", "package.json", "index.ts"),
        "Storage": ("models", "schema", "repository"),
        "Long-running svc": ("supervisor", "worker", "daemon"),
    }
    text = " ".join(os.listdir(path)).lower()
    for dp, dn, fn in os.walk(path):
        if any(s in dp.split(os.sep) for s in SKIP):
            continue
        for name in fn:
            low = name.lower()
            text += " " + low
            if low in ("requirements.txt", "pyproject.toml", "package.json"):
                try:
                    text += " " + open(os.path.join(dp, name), errors="ignore").read().lower()
                except Exception:
                    pass
    for stack, keys in markers.items():
        if any(k in text for k in keys):
            hints.add(stack)
    return sorted(hints)


def suggest_arch_table(path, skill_md):
    """Compare detected stacks against the Architecture Decision table in SKILL.md.
    Returns (detected_stacks, missing_stacks, update_available: bool)."""
    detected = detect_stack_hints(path)
    # parse existing table rows: '| Stack | Pick | Why |'
    rows = []
    if os.path.exists(skill_md):
        for line in open(skill_md, encoding="utf-8"):
            m = re.match(r"\|\s*([A-Za-z /]+?)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|", line)
            if m and m.group(1).strip() not in ("Stack", "-"):
                rows.append(m.group(1).strip())
    covered = set(rows)
    missing = [s for s in detected if s not in covered]
    return detected, missing, bool(missing)


def cleanliness(a):
    score = 0
    notes = []
    if a["tests"] > 0:
        score += 1
    else:
        notes.append("no tests")
    if not a["god_files"]:
        score += 1
    else:
        notes.append(f"{len(a['god_files'])} god-file(s)>400L")
    if a["dirs"]:
        score += 1
    else:
        notes.append("flat/no module dirs")
    return "CLEAN" if score >= 2 and not a["god_files"] else "REVIEW", notes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("repo")
    ap.add_argument("--vault")
    ap.add_argument("--skill", default=None,
                    help="path to SKILL.md for arch-table comparison (default: skill dir SKILL.md)")
    a = ap.parse_args()
    path, cloned = clone_or_use(a.repo)
    info = analyze(path)
    verdict, notes = cleanliness(info)
    name = os.path.basename(path.rstrip("/"))
    snippets = extract_snippets(path)
    # #10 living arch table: compare detected stacks vs SKILL.md decision table
    skill_md = a.skill or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "SKILL.md")
    detected, missing, update_avail = suggest_arch_table(path, skill_md)
    snippet = (
        f"# Template-{name}\n"
        f"source: {a.repo}\nverdict: {verdict}\n"
        f"scanned: {datetime.date.today().isoformat()}\n\n"
        f"## Module boundaries\n" +
        "".join(f"- `{d}/` ({c} files)\n" for d, c in info["dirs"].items()) +
        f"\n## Stats\n- files: {info['n_files']}\n- tests: {info['tests']}\n"
        f"- god-files: {info['god_files'] or 'none'}\n"
        f"\n## Notes\n- " + ("; ".join(notes) if notes else "clean structure") + "\n"
        f"\n## Reusable snippets ({len(snippets)})\n" +
        ("".join(f"- `{f}`: `{s}`\n" for f, s in snippets) if snippets else "- _no public symbols extracted_\n")
        + f"\n## Arch suggestions (#10)\n"
        f"- detected stacks: {', '.join(detected) or '_none_'}\n"
        + (f"- **UPDATE SKILL.md**: missing rows for: {', '.join(missing)}\n"
           f"  add to Architecture Decision table so future scaffolds use them.\n"
           if update_avail else "- arch table already covers detected stacks ✓\n")
    )
    print(snippet)
    # write to vault via resolve_vault (consistent with hashchain.py)
    v = resolve_vault(a.vault)
    os.makedirs(v, exist_ok=True)
    np_ = os.path.join(v, f"Template-{name}.md")
    with open(np_, "w") as f:
        f.write(snippet)
    print(f"\n[vault] wrote {np_}")
    # also drop a reusable snippets file next to the repo (local only)
    if not cloned and snippets:
        sdir = os.path.join(path, "docs")
        os.makedirs(sdir, exist_ok=True)
        with open(os.path.join(sdir, "snippets.md"), "w") as f:
            f.write(f"# Reusable snippets mined from {name}\n\n" +
                    "".join(f"### `{f}`\n```python\n{s}\n```\n\n" for f, s in snippets))
        print(f"[local] wrote {path}/docs/snippets.md")
    if cloned:
        subprocess.run(["rm", "-rf", path])


if __name__ == "__main__":
    main()
