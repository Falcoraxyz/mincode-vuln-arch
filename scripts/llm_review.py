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
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import config

SKIP_DIRS = (".git", "node_modules", "__pycache__", ".ok", "venv", ".venv", "tests", "docs")
EXT = (".py", ".js", ".ts", ".go", ".rs", ".java")
MAX_CHARS = 12000  # cap context sent to the model

# local-first fallback endpoints (no API key needed)
LOCAL_ENDPOINTS = {
    "ollama": "http://localhost:11434/v1",
    "llamacpp": "http://localhost:8080/v1",
}


def detect_backend(model, api_key, base_url):
    """Resolve (api_key, base_url, label). Precedence:
    1. explicit OPENAI_BASE_URL / OPENAI_API_KEY env
    2. Ollama local server (no key)
    3. llama.cpp server (no key)
    4. OpenAI cloud (requires key)
    Returns (api_key, base_url, label, usable: bool)."""
    if base_url and base_url != "https://api.openai.com/v1":
        return api_key or "ollama", base_url, "custom", True
    if api_key:
        return api_key, base_url or "https://api.openai.com/v1", "openai", True
    # probe local servers (HEAD /v1/models)
    for label, url in LOCAL_ENDPOINTS.items():
        try:
            req = urllib.request.Request(url.rstrip("/") + "/models", method="GET")
            with urllib.request.urlopen(req, timeout=2) as r:
                if r.status == 200:
                    return "ollama", url, label, True
        except Exception:
            continue
    # fall back to OpenAI cloud; usable only if a key exists
    return api_key or "", "https://api.openai.com/v1", "openai", bool(api_key)


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
    ap.add_argument("--model", default=None, help="model name (else OPENAI_MODEL / config / gpt-4o-mini)")
    ap.add_argument("--backend", default=None,
                    help="explicit OpenAI-compatible base URL (overrides auto-detect)")
    ap.add_argument("--config", default=None, help="path to mincode.toml")
    a = ap.parse_args()
    cfg = config.load_config(a.config)
    model = a.model or os.environ.get("OPENAI_MODEL") or cfg["llm"].get("model") or "gpt-4o-mini"
    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = (a.backend or os.environ.get("OPENAI_BASE_URL")
                or cfg["llm"].get("base_url") or "https://api.openai.com/v1")
    key, url, label, usable = detect_backend(model, api_key, base_url)
    if not usable:
        print("llm_review: no backend available — set OPENAI_API_KEY, or run a local "
              "Ollama (http://localhost:11434) / llama.cpp server. Skipping (heuristic "
              "audit still applies).")
        sys.exit(0)
    code = collect(a.project)
    if not code:
        print("llm_review: no source files collected.")
        sys.exit(0)
    print(f"llm_review: sending ~{len(code)} chars to {model} via {label} ({url}) ...")
    result = review(code, model, key, url)
    date = datetime.date.today().isoformat()
    name = os.path.basename(os.path.abspath(a.project).rstrip("/"))
    note = (
        f"# Audit-{name}-llm-{date}\n"
        f"source: {a.project}\nmodel: {model}\nbackend: {label}\nreviewed: {date}\n\n"
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
