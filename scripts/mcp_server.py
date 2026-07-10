#!/usr/bin/env python3
"""Minimal stdlib MCP (Model Context Protocol) server for mincode-vuln-arch.

Exposes the toolkit as MCP *tools* over stdio so any MCP-capable agent
(Claude Desktop, Cursor, Zed, Cline, Windsurf, ...) can call it as a native
tool — no shelling out, no skill system, no Obsidian required.

Zero third-party dependencies: speaks the MCP JSON-RPC protocol directly.
Protocol: stdio, with LSP-style ``Content-Length`` framing (2024-11-05 spec)
and also accepts newline-delimited JSON-RPC (2025-03-26). Output uses
Content-Length framing for maximum client compatibility.

Run (foreground, stdio):
    python mcp_server.py

Client config example (claude_desktop_config.json / mcp.json):
    {
      "mcpServers": {
        "mincode": {
          "command": "python",
          "args": ["/path/to/mincode-vuln-arch/scripts/mcp_server.py"]
        }
      }
    }

Tools:
    mincode_audit     -> audit.py     (vuln gate + findings)
    mincode_gen_tests -> gen_tests.py (typed smoke tests)
    mincode_mine      -> sample_repo.py (architecture mining)
    mincode_llm_review-> llm_review.py (logic-flaw review; skips if no backend)
"""
import os
import sys
import io
import json
import runpy

SCRIPTS = os.path.dirname(os.path.abspath(__file__))


# --------------------------------------------------------------------------- #
# Tool definitions (name -> inputSchema + argv builder)
# --------------------------------------------------------------------------- #
TOOLS = [
    {
        "name": "mincode_audit",
        "description": "Audit a project for vulnerabilities (multi-language heuristic + CWE + "
                       "graded gate). Returns findings and an A-F grade. HIGH findings fail the gate.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Path to the project to audit"},
                "threshold": {"type": "integer", "description": "Max HIGH allowed before gate fails (0 = zero-tolerance)"},
                "run_tests": {"type": "boolean", "description": "Run generated smoke tests and fold failures into the grade"},
                "no_vault": {"type": "boolean", "description": "Skip writing the vault note (results still returned)"},
                "sarif": {"type": "string", "description": "Optional path to write a SARIF 2.1.0 report"},
            },
            "required": ["project"],
        },
    },
    {
        "name": "mincode_gen_tests",
        "description": "Generate typed smoke tests for a project (zero-dep unittest).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Path to the project"},
            },
            "required": ["project"],
        },
    },
    {
        "name": "mincode_mine",
        "description": "Mine clean architecture patterns + reusable snippets from a repo or git URL.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {"type": "string", "description": "Repo path or git URL to mine"},
                "no_vault": {"type": "boolean", "description": "Skip writing the vault note"},
            },
            "required": ["repo"],
        },
    },
    {
        "name": "mincode_llm_review",
        "description": "LLM logic-flaw review of a project via an OpenAI-compatible endpoint. "
                       "Auto-detects local Ollama/llama.cpp (offline) or OpenAI. Skips safely if no backend.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project": {"type": "string", "description": "Path to the project"},
                "model": {"type": "string", "description": "Optional model name override"},
                "no_vault": {"type": "boolean", "description": "Skip writing the vault note"},
            },
            "required": ["project"],
        },
    },
]


def _build_argv(name, args):
    if name == "mincode_audit":
        argv = [args["project"]]
        if args.get("threshold") is not None:
            argv += ["--threshold", str(args["threshold"])]
        if args.get("run_tests"):
            argv.append("--run-tests")
        if args.get("no_vault"):
            argv.append("--no-vault")
        if args.get("sarif"):
            argv += ["--sarif", args["sarif"]]
        return "audit.py", argv
    if name == "mincode_gen_tests":
        return "gen_tests.py", [args["project"]]
    if name == "mincode_mine":
        argv = [args["repo"]]
        if args.get("no_vault"):
            argv.append("--no-vault")
        return "sample_repo.py", argv
    if name == "mincode_llm_review":
        argv = [args["project"]]
        if args.get("model"):
            argv += ["--model", args["model"]]
        if args.get("no_vault"):
            argv.append("--no-vault")
        return "llm_review.py", argv
    raise KeyError(name)


def _dispatch(name, args):
    """Run the mapped script, capture stdout, return an MCP tools/call result."""
    try:
        script, argv = _build_argv(name, args)
    except KeyError:
        return {"content": [{"type": "text", "text": f"unknown tool: {name}"}], "isError": True}

    target = os.path.join(SCRIPTS, script)
    if not os.path.exists(target):
        return {"content": [{"type": "text", "text": f"script not found: {target}"}], "isError": True}

    buf = io.StringIO()
    saved_argv, saved_stdout = sys.argv, sys.stdout
    sys.argv = [script] + [str(a) for a in argv]
    if SCRIPTS not in sys.path:
        sys.path.insert(0, SCRIPTS)
    code = 0
    try:
        sys.stdout = buf
        runpy.run_path(target, run_name="__main__")
    except SystemExit as e:
        code = e.code if isinstance(e.code, int) else 0
    except Exception as ex:
        sys.stdout = saved_stdout
        sys.argv = saved_argv
        return {"content": [{"type": "text", "text": f"ERROR: {ex}"}], "isError": True}
    finally:
        sys.stdout = saved_stdout
        sys.argv = saved_argv

    out = buf.getvalue()
    text = out if out else "(no output)"
    text += f"\n\n[exit_code: {code}]"
    return {"content": [{"type": "text", "text": text}], "isError": False}


# --------------------------------------------------------------------------- #
# stdio JSON-RPC transport
# --------------------------------------------------------------------------- #
def _read_message(rfile):
    """Read one JSON-RPC message from a buffered binary reader.

    Accepts both Content-Length framed (2024-11-05) and newline-delimited
    (2025-03-26) input."""
    first = rfile.readline()
    if not first:
        return None
    if first.lstrip().startswith(b"{"):
        return json.loads(first.decode())
    headers = {}
    if b":" in first:
        k, v = first.decode().split(":", 1)
        headers[k.strip().lower()] = v.strip()
    while True:
        line = rfile.readline()
        if not line or line.strip() == b"":
            break
        if b":" in line:
            k, v = line.decode().split(":", 1)
            headers[k.strip().lower()] = v.strip()
    if "content-length" not in headers:
        return None
    n = int(headers["content-length"])
    body = rfile.read(n)
    return json.loads(body.decode())


def _send(msg):
    data = json.dumps(msg).encode()
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(data) + data)
    sys.stdout.buffer.flush()


def _result(mid, payload):
    return {"jsonrpc": "2.0", "id": mid, "result": payload}


def main():
    rfile = sys.stdin.buffer
    while True:
        msg = _read_message(rfile)
        if msg is None:
            break
        method = msg.get("method")
        mid = msg.get("id")
        if method == "initialize":
            _send(_result(mid, {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "mincode-vuln-arch", "version": "1.0"},
            }))
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            _send(_result(mid, {"tools": TOOLS}))
        elif method == "tools/call":
            name = msg.get("params", {}).get("name")
            args = msg.get("params", {}).get("arguments", {}) or {}
            _send(_result(mid, _dispatch(name, args)))
        elif method in ("ping",) or (method and method.endswith("/list")):
            _send(_result(mid, {}))
        else:
            # Unknown request with id: answer empty to avoid a hung client.
            if mid is not None:
                _send(_result(mid, {}))


if __name__ == "__main__":
    main()
