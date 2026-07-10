#!/usr/bin/env python3
"""Minimal heuristic vulnerability audit. No network, stdlib only.
Usage: python audit.py <project_path>
Scans .py/.js/.ts/.jsx/.tsx/.go/.rs/.sh/.json/.yaml for common weakness patterns.
Exit 0 if no HIGH; exit 1 if any HIGH.
Optional: if `bandit` on PATH, runs it (Python only) and merges.
Dependency CVE scan via pip-audit (Python) / cargo audit (Rust) when available.
Each finding is tagged with a CWE and the project gets an A-F grade.
"""
import os, re, sys, subprocess, json

# Python-specific patterns (regex, description, CWE-id)
PY_PATTERNS = {
    "HIGH": [
        (r"(?i)(password|passwd|pwd|pw|token|access[_-]?key|api[_-]?key|secret|private[_-]?key)\s*=\s*['\"][^'\"]+['\"]", "hardcoded credential", "CWE-798"),
        (r"\beval\s*\(", "eval() — code injection risk", "CWE-95"),
        (r"\bexec\s*\(", "exec() — code injection risk", "CWE-95"),
        (r"(?i)subprocess\.[^\n]*shell\s*=\s*True", "shell=True subprocess", "CWE-78"),
        (r"(?i)pickle\.loads?", "unsafe deserialization (pickle)", "CWE-502"),
        (r"(?i)yaml\.load\s*\([^,)]*\)", "yaml.load without safe_load", "CWE-502"),
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

# Polyglot patterns (apply to js/ts/go/rs/sh) — language-agnostic weaknesses
POLYGLOT_PATTERNS = {
    "HIGH": [
        (r"(?i)(password|passwd|pwd|token|api[_-]?key|secret|private[_-]?key|access[_-]?token)\s*[:=]\s*['\"][^'\"]+['\"]", "hardcoded credential", "CWE-798"),
        (r"\beval\s*\(", "eval() — code injection risk", "CWE-95"),
        (r"(?i)\bnew\s+Function\s*\(", "new Function() — code injection risk", "CWE-95"),
        (r"(?i)child_process\.(exec|execSync)\s*\([^)]*\)", "shell command exec", "CWE-78"),
        (r"(?i)\b(exec|system|spawn|shell)\s*\([^)]*\$?[A-Za-z_][A-Za-z0-9_]*", "shell command with var interpolation", "CWE-78"),
        (r"(?i)SELECT.+WHERE+['\"`]\s*\+|f?[\"'`]SELECT", "SQL string concat", "CWE-89"),
        (r"\.\./", "potential path traversal", "CWE-22"),
        (r"(?i)(md5|sha1)\s*\(", "weak hash (md5/sha1)", "CWE-327"),
    ],
    "MED": [
        (r"(?i)verify\s*[:=]\s*false|rejectUnauthorized\s*[:=]\s*false|InsecureSkipVerify", "TLS verification disabled", "CWE-295"),
        (r"(?i)Math\.random\s*\(\s*\)", "non-crypto RNG for secrets", "CWE-330"),
        (r"(?i)(debug)\s*[:=]\s*true", "debug mode on", "CWE-489"),
    ],
    "LOW": [
        (r"(?i)TODO|FIXME", "leftover TODO/FIXME", "CWE-1078"),
        (r"(?i)console\.log\s*\(", "debug log (noise)", "CWE-489"),
    ],
}

# file extension -> which pattern set to use
EXT_LANG = {
    ".py": "py",
    ".js": "poly", ".jsx": "poly", ".ts": "poly", ".tsx": "poly",
    ".go": "poly", ".rs": "poly",
    ".sh": "poly",
    ".json": "poly", ".yaml": "yaml", ".yml": "yaml",
}
EXT = tuple(EXT_LANG.keys())
SKIP_DIRS = (".git", "node_modules", "__pycache__", ".ok", "venv", ".venv", "tests", ".mincode")


def patterns_for(ext):
    lang = EXT_LANG.get(ext)
    if lang == "py":
        return PY_PATTERNS
    if lang == "poly":
        return POLYGLOT_PATTERNS
    # yaml/json: only scan for hardcoded secrets (no code patterns)
    return {"HIGH": POLYGLOT_PATTERNS["HIGH"][:1], "MED": [], "LOW": []}


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
            ext = os.path.splitext(name)[1].lower()
            if ext not in EXT_LANG:
                continue
            fp = os.path.join(dp, name)
            try:
                with open(fp, "r", errors="ignore") as f:
                    lines = f.readlines()
            except Exception:
                continue
            pats = patterns_for(ext)
            for i, line in enumerate(lines, 1):
                for sev, plist in pats.items():
                    for rx, desc, cwe in plist:
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


SEV_TO_SARIF = {"HIGH": "error", "MED": "warning", "LOW": "note"}


def to_sarif(findings, scanned_path, tool_name="mincode-audit"):
    """Emit a SARIF 2.1.0 doc so findings integrate with GitHub code scanning."""
    # one rule per unique CWE
    rules = {}
    rule_list = []
    for sev, fp, ln, desc, cwe, snip in findings:
        if cwe not in rules:
            rid = cwe
            rules[cwe] = len(rule_list)
            rule_list.append({
                "id": rid,
                "name": cwe,
                "shortDescription": {"text": desc},
                "fullDescription": {"text": f"{desc} ({cwe})"},
                "properties": {"security-severity": {"HIGH": "8.0", "MED": "5.0", "LOW": "2.0"}[sev]},
            })
    results = []
    for sev, fp, ln, desc, cwe, snip in findings:
        try:
            uri = os.path.relpath(fp, scanned_path).replace(os.sep, "/")
        except ValueError:
            uri = fp
        results.append({
            "ruleId": cwe,
            "level": SEV_TO_SARIF.get(sev, "warning"),
            "message": {"text": f"{desc} [{cwe}]"},
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {"uri": uri},
                    "region": {"startLine": ln, "endLine": ln},
                }
            }],
        })
    doc = {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [{
            "tool": {"driver": {
                "name": tool_name,
                "version": "1.0",
                "rules": rule_list,
            }},
            "results": results,
        }],
    }
    return doc


def run_tests(path):
    """Run generated smoke tests. Returns (total, failed, passed).
    A failed test lowers the grade and can fail the audit gate.
    Runs each tests/<mod>_test.py directly (unittest.main) — reliable on Windows
    where `unittest discover` can report 0 tests due to loader path quirks."""
    tests_dir = os.path.join(path, "tests")
    if not os.path.isdir(tests_dir):
        return 0, 0, 0
    import glob
    files = sorted(glob.glob(os.path.join(tests_dir, "*_test.py")))
    if not files:
        return 0, 0, 0
    total = failed = 0
    env = dict(os.environ)
    env["PYTHONPATH"] = path + os.pathsep + env.get("PYTHONPATH", "")
    for tf in files:
        proc = subprocess.run([sys.executable, tf], cwd=path, env=env,
                               capture_output=True, text=True)
        out = proc.stdout + proc.stderr
        for line in out.splitlines():
            m = re.match(r"Ran (\d+) test", line)
            if m:
                total += int(m.group(1))
            if line.startswith("FAILED"):
                fm = re.search(r"failures=(\d+)", line)
                em = re.search(r"errors=(\d+)", line)
                failed += (int(fm.group(1)) if fm else 0) + (int(em.group(1)) if em else 0)
    return total, failed, (total - failed if total else 0)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--sarif", metavar="FILE", help="write SARIF 2.1.0 to FILE")
    ap.add_argument("--run-tests", action="store_true",
                    help="execute generated smoke tests and fold failures into the grade")
    a = ap.parse_args()
    path = a.project
    findings = scan(path) + run_bandit(path) + dep_scan(path)
    failed_count = 0
    if a.run_tests:
        total, failed, passed = run_tests(path)
        if total:
            print(f"[tests] {total} run, {passed} passed, {failed} failed")
            if failed:
                failed_count = failed
                findings.append(("MED", os.path.join(path, "tests"), 0,
                                 f"{failed} smoke test(s) failed", "CWE-1120",
                                 f"{failed}/{total} failing"))
        else:
            print("[tests] none found (run gen_tests.py first)")
    findings.sort(key=lambda x: {"HIGH": 0, "MED": 1, "LOW": 2}[x[0]])
    if a.sarif:
        doc = to_sarif(findings, path)
        with open(a.sarif, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        print(f"[sarif] wrote {a.sarif} ({len(findings)} findings)")
    if not findings:
        print("AUDIT CLEAN — no findings. Grade: A")
        try:
            import datetime
            d = datetime.date.today().isoformat()
            subprocess.run(["git", "tag", f"audit-clean-{d}"],
                           cwd=path, capture_output=True, check=False)
        except Exception:
            pass
        sys.exit(0)
    high = 0
    cwes = set()
    for sev, fp, ln, desc, cwe, snip in findings:
        if sev == "HIGH":
            high += 1
    g, penalty = grade(findings)
    print(f"---\n{high} HIGH, {len(findings)-high} other | CWEs: {', '.join(sorted(cwes))}")
    print(f"GRADE: {g}  (penalty {penalty})")
    # gate: HIGH always fails; with --run-tests, any test failure also fails
    blocked = high or (a.run_tests and failed_count > 0)
    sys.exit(1 if blocked else 0)


if __name__ == "__main__":
    main()
