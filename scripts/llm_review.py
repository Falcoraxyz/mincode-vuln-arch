#!/usr/bin/env python3
"""LLM-assisted code review for logic flaws regex audits miss.
Usage: python llm_review.py <project_path> [--vault <dir>] [--model <name>]

Reads source files (excludes tests/), sends them to an OpenAI-compatible chat
endpoint, and asks the model to flag logic bugs / insecure patterns / dead code
that the heuristic audit cannot catch. Writes an [[Audit-<project>-llm-<date>]]
note to the vault. Network + API key required (OPENAI_API_KEY, optional
OPENAI_BASE_URL). No-op-safe: if no key, prints a notice and exits 0.

Stdlib only (urllib). Model defaults to the value of OPENAI_MODEL or
'gpt-4o-mini'.
"""
import os, sys, json, argparse, datetime, urllib.request, urllib.error

SKIP_DIRS = (".git", "node_modules", "__pycache__", ".ok", "venv", ".venv", "tests", "docs")
EXT = (".py", ".js", ".ts", ".go", ".rs", ".java")
MAX_CHARS = 12000  # cap context sent to the model


def resolve_vault(explicit):
    if explicit:
        return explicit
    env = os.path.join(os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes")), ".env")
    try:
        with open(env) as f:
            for line in f:
                if line.startswith("OBSIDIAN_VAULT_PATH="):
                    return line.strip().split("=", 1)[1]
    except Exception:
        pass
    return os.environ.get("OBSIDIAN_VAULT_PATH") or os.path.expanduser("~/Documents/Obsidian Vault")


def collect(path):
    chunks = []
    total = 0
    for dp, dn, fn in os.walk(path):
        if any(s in dp.split(os.sep) for s in SKIP_DIRS):
            continue
        for name in fn:
            if not name.endswith(EXT):
                continue
            fp = os.path.join(dp, name)
            try:
                src = open(fp, encoding="utf-8").read()
            except Exception:
                continue
            if total + len(src) > MAX_CHARS:
                # truncate this file to fit the budget
                src = src[: max(200, MAX_CHARS - total)]
            rel = os.path.relpath(fp, path)
            chunks.append(f"### {rel}\n```\n{src}\n```")
            total += len(src)
            if total >= MAX_CHARS:
                break
        if total >= MAX_CHARS:
            break
    return "\n\n".join(chunks)


def review(codeblock, model, api_key, base_url):
    url = base_url.rstrip("/") + "/chat/completions"
    prompt = (
        "You are a senior code reviewer. Review the following source files for:\n"
        "1. logic bugs / edge cases\n"
        "2. insecure patterns a regex scanner would miss (authz, TOCTOU, injection via data, "
        "unvalidated trust boundaries)\n"
        "3. dead code / unused imports\n"
        "4. anything that would fail under real load\n"
        "Be concise. For each finding give: file, line/area, severity (HIGH/MED/LOW), fix.\n"
        "If clean, say CLEAN. Do not invent issues.\n\n"
        f"{codeblock}"
    )
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode(), method="POST",
        headers={"Authorization": f"Bearer {api_key}",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.loads(r.read().decode())
        return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        return f"[LLM HTTP error {e.code}] {e.read().decode()[:200]}"
    except Exception as e:
        return f"[LLM error] {e}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project")
    ap.add_argument("--vault")
    ap.add_argument("--model", default=os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
    a = ap.parse_args()
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        print("llm_review: no OPENAI_API_KEY set — skipping LLM review (heuristic audit still applies).")
        sys.exit(0)
    code = collect(a.project)
    if not code:
        print("llm_review: no source files collected.")
        sys.exit(0)
    print(f"llm_review: sending ~{len(code)} chars to {a.model} ...")
    result = review(code, a.model, api_key, base_url)
    date = datetime.date.today().isoformat()
    name = os.path.basename(os.path.abspath(a.project).rstrip("/"))
    note = (
        f"# Audit-{name}-llm-{date}\n"
        f"source: {a.project}\nmodel: {a.model}\nreviewed: {date}\n\n"
        f"## LLM review (#9)\n\n{result}\n"
    )
    v = resolve_vault(a.vault)
    os.makedirs(v, exist_ok=True)
    np_ = os.path.join(v, f"Audit-{name}-llm-{date}.md")
    with open(np_, "w") as f:
        f.write(note)
    print(f"[vault] wrote {np_}")
    print("---")
    print(result[:800])


if __name__ == "__main__":
    main()
