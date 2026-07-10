# Audit + Hash-chain: condensed knowledge bank

Condensed from real debugging in this skill's build. Read before touching
`scripts/audit.py` or `scripts/hashchain.py`.

## audit.py — regex gotchas
- `shell=True` detection: pattern MUST be `subprocess\.[^\n]*shell\s*=\s*True`.
  Early version used `[^,]*` which failed because `subprocess.run(..., shell=True)`
  has a comma *before* `shell=True`, so the negated class stopped too early.
- Hardcoded-cred pattern should include `pw|pwd|private[_-]?key`, not just
  `password|passwd|token|...`, or short var names slip through.
- Every pattern is `(regex, description, CWE-id)`. Keep the 3-tuple shape when
  adding rules; `scan()` unpacks `for rx, desc, cwe in pats`.
- CWE -> grade weights: HIGH=10, MED=3, LOW=1. Bands: A(0) B(<=2) C(<=9) D(<=19)
  E(<=39) F(>39). Grade prints with the sorted CWE set for triage.
- dep_scan prefers `pip-audit -r <file> -f json` (needs network for the
  advisory DB). Without `pip-audit` it emits a LOW "install pip-audit" notice
  rather than failing — don't treat absence as clean.

## hashchain.py — design + the re-append bug
- Sign the RAW body (frontmatter EXCLUDED). `verify` strips the `---\n...\n---`
  block then re-derives the HMAC, so the signed bytes must equal what verify
  strips to. If you sign the on-disk file (frontmatter included) the verify
  replay mismatches.
- **Re-append frontmatter bug (fixed):** `append` originally only wrote
  frontmatter `if not body.startswith("---")`. Re-appending an already-chained
  note left the OLD frontmatter in place, so the stored hash/sig described the
  stale body while verify saw fresh content -> false TAMPER at #1. FIX: always
  `body = raw.split("---", 2)[-1].lstrip("\n")` to strip any existing
  frontmatter, then re-sign the clean body and rewrite the file.
- Cross-drive paths: `os.path.relpath(note, vault)` raises `ValueError` when
  note is on C: and vault on D: (Windows). Use `_rel_or_abs` -> falls back to
  `os.path.abspath`. Store absolute path in the manifest in that case.
- HMAC key is per-vault at `<vault>/._chain/.key` (32 random bytes, chmod 600).
  `rotate-key` regenerates it and re-signs every row from current note bodies —
  it CANNOT repair a tampered note (re-signs the tampered body). Add `.key` to
  .gitignore; it must never be committed.

## Windows ops (junction)
- `mklink /J` fails through git-bash `cmd //c "mklink ..."` (quotes get stripped)
  and `os.symlink` raises WinError 1314 (needs SeCreateSymbolicLinkPrivilege).
- RELIABLE: `subprocess.run(f'mklink /J "{src}" "{dst}"', shell=True)` -> rc=0,
  junction created. Use this to link the skill dir on C: to the D: repo so
  Hermes still loads it after moving the source of truth to another drive.
- Consent gate: a terminal command containing `rm -rf` is blocked by Hermes
  unless it's the only operation. Split destructive cleanup into its own call.
