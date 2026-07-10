#!/usr/bin/env python3
"""Repo-root wrapper: delegate to the mincode_vuln_arch.cli dispatcher.

Kept for `python cli.py ...` invocations and as a secondary entry. The canonical
dispatcher lives at scripts/cli.py (package mincode_vuln_arch.cli).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts"))
import cli as _cli

if __name__ == "__main__":
    sys.exit(_cli.main())
