#!/usr/bin/env python3
"""Local append-only hash-chain for Obsidian vault notes. No network.
Tamper-evident: each note links to previous note hash.

Usage:
  hashchain.py append <note_path> [--vault <dir>]
  hashchain.py verify [--vault <dir>]
  hashchain.py status [--vault <dir>]

Manifest: <vault>/._chain/manifest.jsonl  (append-only)
Each appended note gets frontmatter: chain_prev, chain_hash, chain_ts.
"""
import os, sys, json, hashlib, datetime, argparse

MANIFEST_REL = os.path.join("._chain", "manifest.jsonl")


def vault_path(explicit):
    if explicit:
        return explicit
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


def append(note_path, v):
    with open(note_path, encoding="utf-8") as f:
        body = f.read()
    rows = read_manifest(v)
    prev = rows[-1]["chain_hash"] if rows else "GENESIS"
    h = sha256(prev + "|" + body)
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    front = (f"---\nchain_prev: {prev}\nchain_hash: {h}\nchain_ts: {ts}\n---\n\n")
    # prepend frontmatter only if not already present
    if not body.startswith("---"):
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(front + body)
    rows.append({"chain_hash": h, "prev": prev, "note": os.path.relpath(note_path, v),
                 "ts": ts, "len": len(body)})
    write_manifest(v, rows)
    print(f"appended {os.path.basename(note_path)}  hash={h[:12]}  prev={prev[:12]}")


def verify(v):
    rows = read_manifest(v)
    if not rows:
        print("chain empty — nothing to verify.")
        return 0
    prev = "GENESIS"
    for i, r in enumerate(rows, 1):
        if r["prev"] != prev:
            print(f"TAMPER at #{i}: prev {r['prev'][:12]} != expected {prev[:12]}")
            return 1
        # re-read note body if exists and re-check linkage
        np_ = os.path.join(v, r["note"])
        if os.path.exists(np_):
            with open(np_, encoding="utf-8") as f:
                body = f.read()
            if "chain_hash: " + r["chain_hash"] not in body:
                print(f"TAMPER at #{i}: note {r['note']} hash mismatch")
                return 1
        prev = r["chain_hash"]
    print(f"CHAIN OK — {len(rows)} entries, head {prev[:12]}")
    return 0


def status(v):
    rows = read_manifest(v)
    print(f"vault: {v}\nentries: {len(rows)}")
    if rows:
        print(f"head: {rows[-1]['chain_hash'][:12]} @ {rows[-1]['ts']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["append", "verify", "status"])
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


if __name__ == "__main__":
    main()
