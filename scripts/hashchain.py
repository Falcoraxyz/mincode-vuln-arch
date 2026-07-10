#!/usr/bin/env python3
"""Local append-only hash-chain for Obsidian vault notes. No network.
Tamper-evident AND forged-resistant: each note links to previous note hash and
is signed with a local HMAC key (vault/._chain/.key, auto-generated).

Usage:
  hashchain.py append <note_path> [--vault <dir>]
  hashchain.py verify [--vault <dir>]
  hashchain.py status [--vault <dir>]
  hashchain.py rotate-key [--vault <dir>]   # new key, re-sign whole chain

Manifest: <vault>/._chain/manifest.jsonl  (append-only)
Each appended note gets frontmatter: chain_prev, chain_hash, chain_ts.
"""
import os, sys, json, re, hashlib, hmac, datetime, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config
from pathlib import Path

MANIFEST_REL = os.path.join("._chain", "manifest.jsonl")
KEY_PATH_REL = os.path.join("._chain", ".key")


def vault_path(explicit):
    if explicit:
        return explicit
    cfg_path = config.load_config().get("vault", {}).get("path")
    if cfg_path:
        return cfg_path
    env = os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), ".env")
    v = None
    try:
        with open(env) as f:
            for line in f:
                if line.startswith("OBSIDIAN_VAULT_PATH="):
                    v = line.strip().split("=", 1)[1]
    except Exception:
        pass
    return v or os.path.expanduser("~/Documents/Obsidian Vault")


def sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _load_key(v):
    kp = os.path.join(v, KEY_PATH_REL)
    if not os.path.exists(kp):
        os.makedirs(os.path.dirname(kp), exist_ok=True)
        key = os.urandom(32)
        # mode 600-ish (best effort on Windows)
        with open(kp, "wb") as f:
            f.write(key)
        try:
            os.chmod(kp, 0o600)
        except Exception:
            pass
        return key
    with open(kp, "rb") as f:
        return f.read()


def sign(key, prev, body):
    msg = (prev + "|" + body).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def read_manifest(v):
    mf = os.path.join(v, MANIFEST_REL)
    if not os.path.exists(mf):
        return []
    with open(mf) as f:
        return [json.loads(l) for l in f if l.strip()]


def write_manifest(v, rows):
    mf = os.path.join(v, MANIFEST_REL)
    os.makedirs(os.path.dirname(mf), exist_ok=True)
    with open(mf, "w") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")


def _rel_or_abs(note_path, v):
    try:
        return os.path.relpath(note_path, v)
    except ValueError:
        # cross-drive (Windows): store absolute path
        return os.path.abspath(note_path)


def append(note_path, v):
    key = _load_key(v)
    with open(note_path, encoding="utf-8") as f:
        raw = f.read()
    # strip any existing frontmatter so we re-sign the clean body
    body = raw
    if body.startswith("---"):
        body = body.split("---", 2)[-1].lstrip("\n")
    rows = read_manifest(v)
    prev = rows[-1]["chain_hash"] if rows else "GENESIS"
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    # hash + sign the RAW body (frontmatter excluded) so verify can strip+replay
    h = sha256(prev + "|" + body)
    sig = sign(key, prev, body)
    # write fresh frontmatter (without chaining hash into itself)
    front = (f"---\nchain_prev: {prev}\nchain_hash: {h}\nchain_ts: {ts}\n---\n\n")
    with open(note_path, "w", encoding="utf-8") as f:
        f.write(front + body)
    rows.append({"chain_hash": h, "prev": prev, "note": _rel_or_abs(note_path, v),
                 "ts": ts, "len": len(body), "sig": sig})
    write_manifest(v, rows)
    print(f"appended {os.path.basename(note_path)}  hash={h[:12]}  prev={prev[:12]}")


def verify(v):
    key = _load_key(v)
    rows = read_manifest(v)
    if not rows:
        print("chain empty — nothing to verify.")
        return 0
    prev = "GENESIS"
    for i, r in enumerate(rows, 1):
        if r["prev"] != prev:
            print(f"TAMPER at #{i}: prev {r['prev'][:12]} != expected {prev[:12]}")
            return 1
        # re-read note body if exists and re-check linkage + signature
        np_ = os.path.join(v, r["note"])
        if os.path.exists(np_):
            with open(np_, encoding="utf-8") as f:
                content = f.read()
            if "chain_hash: " + r["chain_hash"] not in content:
                print(f"TAMPER at #{i}: note {r['note']} hash mismatch")
                return 1
            # strip frontmatter to recover the raw signed body
            raw = content
            if raw.startswith("---"):
                raw = raw.split("---", 2)[-1].lstrip("\n")
            expect = sign(key, r["prev"], raw)
            if not hmac.compare_digest(r.get("sig", ""), expect):
                print(f"FORGE at #{i}: note {r['note']} signature invalid (key mismatch/tampered)")
                return 1
        else:
            # note missing: verify stored sig against stored hash (defense if body gone)
            expect = sign(key, r["prev"], r["chain_hash"])
            if not hmac.compare_digest(r.get("sig", ""), expect):
                print(f"FORGE at #{i}: row signature invalid (missing note, key mismatch)")
                return 1
        prev = r["chain_hash"]
    print(f"CHAIN OK — {len(rows)} entries, head {prev[:12]} (HMAC-verified)")
    return 0


def rotate_key(v):
    # generate new key, re-sign every row with current bodies
    new_key = os.urandom(32)
    kp = os.path.join(v, KEY_PATH_REL)
    os.makedirs(os.path.dirname(kp), exist_ok=True)
    with open(kp, "wb") as f:
        f.write(new_key)
    try:
        os.chmod(kp, 0o600)
    except Exception:
        pass
    rows = read_manifest(v)
    prev = "GENESIS"
    for r in rows:
        np_ = os.path.join(v, r["note"])
        if os.path.exists(np_):
            with open(np_, encoding="utf-8") as f:
                body = f.read()
            r["sig"] = sign(new_key, prev, body)
        else:
            r["sig"] = sign(new_key, prev, r["chain_hash"])
        prev = r["chain_hash"]
    write_manifest(v, rows)
    print(f"rotated key, re-signed {len(rows)} entries.")


def status(v):
    key = _load_key(v)
    rows = read_manifest(v)
    print(f"vault: {v}\nentries: {len(rows)}")
    if rows:
        print(f"head: {rows[-1]['chain_hash'][:12]} @ {rows[-1]['ts']}")
    print(f"key: present ({os.path.getsize(os.path.join(v, KEY_PATH_REL))} bytes)")


CWE_RE = re.compile(r"(CWE-\d+)")
AUDIT_RE = re.compile(r"^Audit-(.+?)-(\d{4}-\d{2}-\d{2})\.md$")


def _audit_notes(v, project):
    """Return [(ts, date, set_of_cwes)] for Audit-<project>-* notes, newest last."""
    out = []
    for np_ in sorted(os.listdir(v)):
        m = AUDIT_RE.match(np_)
        if not m or m.group(1) != project:
            continue
        try:
            ts = datetime.datetime.fromisoformat(
                open(os.path.join(v, np_), encoding="utf-8").read().split("reviewed: ", 1)[1].split("\n", 1)[0])
        except Exception:
            ts = datetime.datetime.min
        cwes = set(CWE_RE.findall(open(os.path.join(v, np_), encoding="utf-8").read()))
        out.append((ts, m.group(2), cwes))
    out.sort(key=lambda x: x[0])
    return out


def diff_project(v, project):
    """Regression diff: compare the latest Audit-<project>-* note against the
    previous one. Prints NEW / FIXED / PERSISTENT CWEs. Returns 0 if no new
    findings vs previous, 1 if new findings appeared (regression)."""
    notes = _audit_notes(v, project)
    if not notes:
        print(f"no Audit-{project}-* notes found in vault.")
        return 0
    if len(notes) == 1:
        print(f"only one audit for '{project}' ({notes[0][1]}) — {len(notes[0][2])} CWE(s): "
              f"{', '.join(sorted(notes[0][2])) or 'none'}")
        return 0
    prev_ts, prev_date, prev_cwes = notes[-2]
    cur_ts, cur_date, cur_cwes = notes[-1]
    new = cur_cwes - prev_cwes
    fixed = prev_cwes - cur_cwes
    persistent = cur_cwes & prev_cwes
    print(f"vault regression diff for '{project}':")
    print(f"  prev: {prev_date} ({len(prev_cwes)} CWE)")
    print(f"  curr: {cur_date} ({len(cur_cwes)} CWE)")
    if new:
        print(f"  NEW ({len(new)}): {', '.join(sorted(new))}")
    if fixed:
        print(f"  FIXED ({len(fixed)}): {', '.join(sorted(fixed))}")
    if persistent:
        print(f"  PERSISTENT ({len(persistent)}): {', '.join(sorted(persistent))}")
    if not new and not fixed and not persistent:
        print("  no CWE findings in either audit.")
    return 1 if new else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["append", "verify", "status", "rotate-key", "diff"])
    ap.add_argument("note", nargs="?")
    ap.add_argument("--vault")
    a = ap.parse_args()
    v = vault_path(a.vault)
    if a.cmd == "append":
        if not a.note:
            print("append needs <note_path>"); sys.exit(2)
        append(a.note, v)
    elif a.cmd == "verify":
        sys.exit(verify(v))
    elif a.cmd == "status":
        status(v)
    elif a.cmd == "rotate-key":
        rotate_key(v)
    elif a.cmd == "diff":
        if not a.note:
            print("diff needs <project>"); sys.exit(2)
        sys.exit(diff_project(v, a.note))


if __name__ == "__main__":
    main()
