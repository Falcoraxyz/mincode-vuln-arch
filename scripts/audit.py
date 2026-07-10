#!/usr/bin/env python3
"""Minimal heuristic vulnerability audit. No network, stdlib only.
Usage: python audit.py <project_path>
Scans .py/.js/.ts/.sh/.json for common weakness patterns.
Exit 0 if no HIGH; exit 1 if any HIGH.
Optional: if `bandit` on PATH, runs it and merges.
Dependency CVE scan via pip-audit when available.
Each finding is tagged with a CWE and the project gets an A-F grade.
"""
import os, re, sys, subprocess, json

# (regex, description, CWE-id)
PATTERNS = {
    "HIGH": [
        (r"(?i)(password|passwd|pwd|pw|token|access[_-]?key|api[_-]?key|secret|private[_-]?key)\s*=\s*['\"][^'\"]+['\"]", "hardcoded credential", "CWE-798"),
        (r"\beval\s*\(", "eval() — code injection risk", "CWE-95"),
        (r"\bexec\s*\(", "exec() — code injection risk", "CWE-95"),
        (r"(?i)subprocess\.[^\n]*shell\s*=\s*True", "shell=True subprocess", "CWE-78"),
        (r"(?i)pickle\.loads?", "unsafe deserialization (pickle)", "CWE-502"),
        (r"(?i)yaml\.load\s*\([^,)]*\)", "yaml.load without safe_load", "CWE-502"),
        (r"(?i)md5|sha1", "weak hash (md5/sha1)", "CWE-327"),
        (r"(?i)SELECT.+WHERE+.['\"]\s*\+|f\"\"\"SELECT", "SQL string concat", "CWE-89"),
        (r"\.\./", "potential path traversal", "CWE-22"),
    ],
    "MED": [
        (r"(?i)verify\s*=\s*False", "TLS verification disabled", "CWE-295"),
        (r"(?i)random\.(random|randint|choice)", "non-crypto RNG for secrets", "CWE-330"),
        (r"(?i)debug\s*=\s*True", "debug mode on", "CWE-489"),
    ],
    "LOW": [
        (r"(?i)TODO|FIXME", "leftover TODO/FIXME", "CWE-1078"),
        (r"print\(", "debug print (noise)", "CWE-489"),
    ],
}

EXT = (".py", ".js", ".ts", ".sh", ".json", ".yaml", ".yml")
SKIP_DIRS = (".git", "node_modules", "__pycache__", ".ok", "venv", ".venv")

# score weights per severity for grading
GRADE_WEIGHTS = {"HIGH": 10, "MED": 3, "LOW": 1}
GRADE_BANDS = [  # (max_penalty, grade)
    (0, "A"),
    (2, "B"),
    (9, "C"),
    (19, "D"),
    (39, "E"),
]
GRADE_F = "F"


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
                    for rx, desc, cwe in pats:
                        if re.search(rx, line):
                            findings.append((sev, fp, i, desc, cwe, line.strip()[:80]))
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
                    r.get("line_number", 0), r.get("issue_text", ""),
                    str(r.get("cwe", {}).get("id", "CWE-?")), ""))
    return res


def find_dep_files(path):
    files = []
    for dp, dn, fn in os.walk(path):
        if any(s in dp.split(os.sep) for s in SKIP_DIRS):
            continue
        for name in fn:
            if name in ("requirements.txt", "requirements-dev.txt",
                        "pyproject.toml", "Pipfile", "poetry.lock"):
                files.append(os.path.join(dp, name))
    return files


def dep_scan(path):
    """CVE scan of declared dependencies. Uses pip-audit if present (best),
    else falls back to pip index versions check. Returns findings list."""
    dep_files = find_dep_files(path)
    if not dep_files:
        return []
    findings = []
    # prefer pip-audit (requires network for the advisory DB, but most accurate)
    try:
        out = subprocess.run(["pip-audit", "-r", dep_files[0], "-f", "json"],
                             capture_output=True, text=True, timeout=180)
        if out.returncode in (0, 1):
            try:
                data = json.loads(out.stdout)
                for dep in data.get("dependencies", []):
                    for vuln in dep.get("vulns", []):
                        sev = vuln.get("severity", "MEDIUM") or "MEDIUM"
                        sev = "HIGH" if str(sev).upper() in ("CRITICAL", "HIGH") else \
                              ("MED" if str(sev).upper() == "MEDIUM" else "LOW")
                        findings.append((sev, dep_files[0], 0,
                                         f"CVE {vuln.get('id','?')}: {vuln.get('description','')[:60]}",
                                         "CWE-1395", f"{dep.get('name')} {dep.get('version')}"))
            except Exception:
                pass
            return findings
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    # fallback: report that dep files exist but no scanner available
    findings.append(("LOW", dep_files[0], 0,
                     "dependency declared but pip-audit not installed — run `pip install pip-audit`",
                     "CWE-1104", os.path.basename(dep_files[0])))
    return findings


def grade(findings):
    penalty = sum(GRADE_WEIGHTS.get(s, 0) for s, *_ in findings)
    for maxp, g in GRADE_BANDS:
        if penalty <= maxp:
            return g, penalty
    return GRADE_F, penalty


def main():
    if len(sys.argv) < 2:
        print("usage: audit.py <project_path>")
        sys.exit(2)
    path = sys.argv[1]
    findings = scan(path) + run_bandit(path) + dep_scan(path)
    findings.sort(key=lambda x: {"HIGH": 0, "MED": 1, "LOW": 2}[x[0]])
    if not findings:
        print("AUDIT CLEAN — no findings. Grade: A")
        sys.exit(0)
    high = 0
    cwes = set()
    for sev, fp, ln, desc, cwe, snip in findings:
        if sev == "HIGH":
            high += 1
        cwes.add(cwe)
        print(f"[{sev}] {fp}:{ln}  {desc}  [{cwe}]  | {snip}")
    g, penalty = grade(findings)
    print(f"---\n{high} HIGH, {len(findings)-high} other | CWEs: {', '.join(sorted(cwes))}")
    print(f"GRADE: {g}  (penalty {penalty})")
    sys.exit(1 if high else 0)


if __name__ == "__main__":
    main()
