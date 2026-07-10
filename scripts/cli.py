#!/usr/bin/env python3
"""mincode — single entrypoint for the mincode-vuln-arch toolkit.

Canonical dispatcher, installed as the `mincode` console script
(`mincode_vuln_arch.cli:main`) and imported by the repo-root `cli.py` /
`mincode.py` wrappers. Zero dependencies (stdlib only) — runs anywhere
Python 3.8+ is available.

Commands:
    mincode gen <project>            -> proj_gen.py   (scaffold minimal project)
    mincode tests <project>          -> gen_tests.py  (typed smoke tests)
    mincode audit <project>          -> audit.py      (vuln audit + gate)
    mincode mine <repo>              -> sample_repo.py (mine clean architecture)
    mincode llm <project>            -> llm_review.py (logic-flaw review)
    mincode vault <cmd> [project]    -> hashchain.py  (append/verify/diff/status)
    mincode moc                      -> vault_index.py (rebuild Obsidian MOC)
    mincode learn                    -> cross_learn.py (cross-project learnings)
    mincode ci <repo>                -> gen_ci.py     (generate CI gate workflow)
    mincode init <repo>              -> scaffold mincode.toml + CI into <repo>

All extra args (--vault, --no-vault, --sarif, --threshold, ...) pass through.
Portable: no hardcoded paths, vault defaults to ./mincode-vault when unset.
"""
import os
import sys
import argparse

# scripts live in this package dir. When running from the repo-root wrappers,
# fall back to ../scripts so `import config` still resolves.
HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = HERE if os.path.exists(os.path.join(HERE, "audit.py")) else os.path.join(os.path.dirname(HERE), "scripts")


COMMANDS = {
    "gen": ("proj_gen.py", "scaffold a minimal project"),
    "tests": ("gen_tests.py", "generate typed smoke tests"),
    "audit": ("audit.py", "vulnerability audit + CI gate"),
    "mine": ("sample_repo.py", "mine clean architecture from a repo"),
    "llm": ("llm_review.py", "LLM logic-flaw review"),
    "moc": ("vault_index.py", "rebuild Obsidian Map of Content"),
    "learn": ("cross_learn.py", "cross-project CWE learnings"),
    "ci": ("gen_ci.py", "generate GitHub Actions audit-gate workflow"),
}


def _run(script, argv):
    target = os.path.join(SCRIPTS, script)
    if not os.path.exists(target):
        sys.stderr.write(f"mincode: script not found: {target}\n")
        return 2
    import runpy
    saved = sys.argv
    sys.argv = [script] + list(argv)
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    try:
        runpy.run_path(target, run_name="__main__")
        return 0
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    finally:
        sys.argv = saved


def _init(repo):
    """Drop mincode.toml.example + generate CI into <repo> so any agent can
    enable the audit gate with one command."""
    repo = os.path.abspath(repo)
    os.makedirs(repo, exist_ok=True)
    toml_dst = os.path.join(repo, "mincode.toml")
    if not os.path.exists(toml_dst):
        src = os.path.join(SCRIPTS, "mincode.toml.example")
        if os.path.exists(src):
            with open(src) as f:
                content = f.read()
            with open(toml_dst, "w") as f:
                f.write(content)
            print(f"[init] wrote {toml_dst}")
    sys.path.insert(0, SCRIPTS)
    import runpy
    sys.argv = ["gen_ci.py", repo]
    try:
        runpy.run_path(os.path.join(SCRIPTS, "gen_ci.py"), run_name="__main__")
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 0
    return 0


def main():
    ap = argparse.ArgumentParser(
        prog="mincode",
        description="mincode-vuln-arch toolkit — minimal code gen + vuln audit + arch mining",
    )
    ap.add_argument("--version", action="version", version="mincode 1.0")
    sub = ap.add_subparsers(dest="cmd", metavar="<command>")

    for name, (script, help_) in COMMANDS.items():
        p = sub.add_parser(name, help=help_)
        p.add_argument("args", nargs=argparse.REMAINDER, help=f"args forwarded to {script}")

    pv = sub.add_parser("vault", help="hash-chain vault ops (append/verify/status/rotate-key/diff)")
    pv.add_argument("args", nargs=argparse.REMAINDER, help="forwarded to hashchain.py")

    pi = sub.add_parser("init", help="scaffold mincode.toml + CI into a repo")
    pi.add_argument("repo", nargs="?", default=".")

    args = ap.parse_args()
    if not args.cmd:
        ap.print_help()
        return 0
    if args.cmd == "init":
        return _init(args.repo)
    if args.cmd == "vault":
        return _run("hashchain.py", args.args)
    script, _ = COMMANDS[args.cmd]
    return _run(script, args.args)


if __name__ == "__main__":
    sys.exit(main())
