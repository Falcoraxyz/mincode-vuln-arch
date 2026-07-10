# mincode-vuln-arch — roadmap & iteration workflow

## How this user iterates on the skill (the "oke" loop)
The owner drives skill evolution with a numbered idea list, then says **"oke"**
to mean: *implement the next sensible item end-to-end* — code + test + commit +
push to GitHub (Falcoraxyz) + bump SKILL.md/README feature table. Do NOT re-ask
between sub-steps when the path is clear. After each item, report what shipped
and the new push SHA.

Order of operations per item:
1. Read the relevant script (don't assume current contents — it changes often).
2. Implement, keeping everything **stdlib-only / zero-dep** unless the item
   explicitly needs a network/SDK extra (e.g. LLM review).
3. Test against a throwaway fixture repo under `$USERPROFILE/_mc_testN/`.
4. Wire the new capability into SKILL.md (a `### Nx.` section) + README feature
   table + (if a new script) the layout tree.
5. Commit on `master` as `Falcoraxyz` (`git -c user.name=... -c user.email=...`)
   and `git push origin master`.
6. Report the new SHA + what was verified.

## Done (original 10 + second round)
#1 dep CVE (pip-audit) · #2 CWE+grade · #3 HMAC chain · #4 snippet · #5 gen_tests
· #6 auto-git · #7 MOC · #8 cross-learn · #9 LLM review · #10 living arch table
· #1b CI gate (gen_ci.py) · #2b test-execution gate (audit.py --run-tests)
· #3b multi-language audit · #4b SARIF export · #7b HTML report (audit.py --report)
· #8b assertion-aware gen_tests · #9b arch auto-apply (sample_repo.py --apply-arch)

## Pending backlog (from the second ideation pass)
- #5 **Local LLM** — `llm_review.py` should auto-detect Ollama / llama.cpp
  endpoints so it works offline (no OPENAI_API_KEY). Matches the local-first
  philosophy.
- #6 **Vault diff / regression** — `hashchain.py diff <project>` shows new
  findings since the last audit of the same project (not just integrity verify).
- #10 **Config file** — `mincode.toml` for threshold / vault path / model /
  skip-dirs, replacing CLI flags.

## Repo presentation (done)
README rewritten with badges + feature table + how-it-works diagram; LICENSE
Apache-2.0; GitHub description + topics set. Keep README in sync after features.

## Regression lesson captured this round (audit.py edit discipline)
When editing `audit.py`'s `main()`, the per-finding loop BODY
(`cwes.add(cwe)` + `print(f"[{sev}] ...")`) is easy to accidentally delete during
a larger patch (e.g. while changing the exit logic). Symptom: findings still
computed and graded, but **nothing prints** and the `CWEs:` line comes out empty
— yet the gate still fails on HIGH. Always keep the `for sev, fp, ln, desc, cwe,
snip in findings:` loop with both `cwes.add(cwe)` and the `print`, separate from
the `high` count and the final `sys.exit`. Re-test with `audit.py <repo>
--run-tests` on a deliberately broken test to confirm the `[MED]`/`[HIGH]` lines
AND the `CWEs:` set actually print.
