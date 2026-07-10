#!/usr/bin/env python3
"""Minimal heuristic vulnerability audit. No network, stdlib only.
Usage: python audit.py <project_path>
Scans .py/.js/.ts/.sh/.json for common weakness patterns.
Exit 0 if no HIGH; exit 1 if any HIGH.
Optional: if `bandit` on PATH, runs it and merges.
"""
import os, re, sys, subprocess, json

PATTERNS = {
    "HIGH": [
        (r"(?i)(password|passwd|pwd|token|access[_-]?key|api[_-]?key|secret)\s*=\s*['\"][^'\"]+['\"]", "hardcoded credential"),
        (r"\beval\s*\(", "eval() — code injection risk"),
        (r"\bexec\s*\(", "exec() — code injection risk"),
        (r"(?i)subprocess\.[^\n]*shell\s*=\s*True", "shell=True subprocess"),
        (r"(?i)pickle\.loads?", "unsafe deserialization (pickle)"),
        (r"(?i)yaml\.load\s*\([^,)]*\)", "yaml.load without safe_load"),
        (r"(?i)md5|sha1", "weak hash (md5/sha1)"),
        (r"(?i)SELECT.+WHERE.+['\"]\s*\+|f\"\"\"SELECT", "SQL string concat"),
        (r"\.\./", "potential path traversal"),
    ],
    "MED": [
        (r"(?i)verify\s*=\s*False", "TLS verification disabled"),
        (r"(?i)random\.(random|randint|choice)", "non-crypto RNG for secrets"),
        (r"(?i)debug\s*=\s*True", "debug mode on"),
    ],
    "LOW": [
        (r"(?i)TODO|FIXME", "leftover TODO/FIXME"),
        (r"print\(", "debug print (noise)"),
    ],
}

EXT = (".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml")
SKIP_DIRS = (".git", "node_modules", "__pycache__", ".ok", "venv", ".venv")


def scan(path):
    findings = []
    for dp, dn, fn in os.walk(path):
        if any(s in dp.split(os.sep) for s in SKIP_DIRS):
            continue
        for name in fn:
            if not name.endswith(EXT):
                continue
            fp = os.path.join(dp, name)
            try:
                with open(fp, "r", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue
            for i, line in enumerate(lines, 1):
                for sev, pats in PATTERNS.items():
                    for rx, desc in pats:
                        if re.search(rx, line):
                            findings.append((sev, fp, i, desc, line.strip()[:80]))
    return findings


def run_bandit(path):
    try:
        out = subprocess.run(["bandit", "-r", path, "-f", "json"],
                             capture_output=True, text=True, timeout=120)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    try:
        data = json.loads(out.stdout)
    except Exception:
        return []
    res = []
    for r in data.get("results", []):
        res.append(("HIGH" if r.get("issue_severity") in ("HIGH", "MEDIUM")
                    else "LOW", r.get("filename", "?"),
                    r.get("line_number", 0), r.get("issue_text", ""), ""))
    return res


def main():
    if len(sys.argv) < 2:
        print("usage: audit.py <project_path>")
        sys.exit(2)
    path = sys.argv[1]
    findings = scan(path) + run_bandit(path)
    findings.sort(key=lambda x: {"HIGH": 0, "MED": 1, "LOW": 2}[x[0]])
    if not findings:
        print("AUDIT CLEAN — no findings.")
        sys.exit(0)
    high = 0
    for sev, fp, ln, desc, snip in findings:
        if sev == "HIGH":
            high += 1
        print(f"[{sev}] {fp}:{ln}  {desc}  | {snip}")
    print(f"---\n{high} HIGH, {len(findings)-high} other")
    sys.exit(1 if high else 0)


if __name__ == "__main__":
    main()
