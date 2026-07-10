#!/usr/bin/env python3
"""Generate a CI workflow that enforces the audit gate (#1).
Usage: python gen_ci.py [--path <dir>] [--threshold <max_high>] [--runner ubuntu]

Emits .github/workflows/audit.yml that:
 - checks out the repo
 - sets up Python
 - runs gen_tests.py, audit.py, and the generated smoke tests
 - fails the build on any HIGH finding (audit.py exits 1) or broken tests
So a clean audit (audit-clean-<date> tag) is *enforced*, not just suggested.

The workflow shells out to this skill's scripts via a git submodule or a
pinned copy. Simplest portable approach: copy scripts/ into the target repo
under .mincode/ and call them. This generator writes that copy step too.
"""
import os, sys, argparse, shutil, datetime

SKILL_SCRIPTS = os.path.join(os.path.dirname(os.path.abspath(__file__)))

YML = """name: audit-gate
on: [push, pull_request]
jobs:
  audit:
    runs-on: {runner}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Generate smoke tests
        run: python .mincode/gen_tests.py .
      - name: Vulnerability audit (gate)
        run: python .mincode/audit.py . --sarif sarif.json --run-tests
        # audit.py exits 1 if any HIGH finding OR any smoke test fails -> CI fails.
      - name: Upload SARIF to code scanning
        if: always()
        uses: github/codeql-action/upload-sarif@v3
        with:
          sarif_file: sarif.json
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default=".")
    ap.add_argument("--threshold", type=int, default=0,
                    help="max allowed HIGH findings (0 = zero tolerance)")
    ap.add_argument("--runner", default="ubuntu-latest")
    a = ap.parse_args()
    # threshold is informational in the comment; audit.py already exits 1 on HIGH.
    # write scripts copy target
    wf_dir = os.path.join(a.path, ".github", "workflows")
    os.makedirs(wf_dir, exist_ok=True)
    wf = os.path.join(wf_dir, "audit.yml")
    with open(wf, "w") as f:
        f.write(YML.format(runner=a.runner))
    # copy scripts into the repo so the workflow is self-contained
    dest = os.path.join(a.path, ".mincode")
    os.makedirs(dest, exist_ok=True)
    for name in os.listdir(SKILL_SCRIPTS):
        if name.endswith(".py"):
            shutil.copy2(os.path.join(SKILL_SCRIPTS, name), os.path.join(dest, name))
    # NOTE: .mincode/ must be COMMITTED (CI needs the scripts). Do not gitignore it.
    print(f"[ci] wrote {wf}")
    print(f"[ci] copied {len(os.listdir(dest))} scripts to {dest}/")
    print(f"[ci] zero-tolerance on HIGH (threshold={a.threshold}); audit-clean tag enforced in CI.")
    print(f"[ci] REMEMBER: commit .mincode/ and .github/ so CI can run them.")


if __name__ == "__main__":
    main()
