#!/usr/bin/env python3
"""Research-only Codex app-server MCP elicitation smoke.

Starts an ephemeral Codex app-server process with a *process-scoped* MCP
server override, calls a non-secret probe tool, and resolves the resulting
form request in this synthetic client. It does not modify Codex global config,
install plugins, read secrets, call a language model, or open UI windows.

This exercises the *app-server event transport*, NOT the Codex Desktop GUI.
"""
import json
import os
from pathlib import Path
import selectors
import subprocess
import sys
import time

from stdio_probe import DEMO_MARKER, DEMO_TOOL_NAME

ROOT = Path(__file__).resolve().parents[2]
PROBE = Path(__file__).resolve().with_name("stdio_probe.py")
SERVER = "secret_drop_form_probe"


def send(proc, obj):
    proc.stdin.write(json.dumps(obj, separators=(",", ":")) + "\n")
    proc.stdin.flush()


def run() -> int:
    public_demo = '--public-demo' in sys.argv
    if not PROBE.is_file():
        print("PILOT_ERROR=probe_source_not_found")
        return 2
    args = [
        "codex", "app-server", "--stdio",
        "-c", f'mcp_servers.{SERVER}.command="python3"',
        "-c", f'mcp_servers.{SERVER}.args=["-I","{PROBE}"]',
    ]
    proc = subprocess.Popen(
        args, cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True, bufsize=1,
    )
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + 25.0
    thread_id = None
    pending_call = False
    elicitation_seen = False
    tool_result_seen = False
    demo_marker_visible = False
    init_ack = False
    try:
        send(proc, {
            "id": 1, "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "secret_drop_elicitation_pilot",
                    "title": "Secret Drop Elicitation Test Client",
                    "version": "0.0.1",
                },
                "capabilities": {
                    "experimentalApi": True,
                    "mcpServerOpenaiFormElicitation": True,
                },
            },
        })
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                print("APPSERVER_EXITED=" + str(proc.returncode))
                return 2
            events = sel.select(timeout=0.5)
            if not events:
                continue
            line = proc.stdout.readline()
            if not line:
                print("APPSERVER_EOF")
                return 2
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("id") == 1:
                if "error" in msg:
                    print("INIT_ERROR=" + str(msg["error"].get("message")))
                    return 2
                init_ack = True
                print("INIT_ACK=yes")
                send(proc, {"method": "initialized", "params": {}})
                send(proc, {
                    "id": 2, "method": "thread/start",
                    "params": {
                        "cwd": str(ROOT),
                        "approvalPolicy": "on-request",
                        "sandbox": "read-only",
                        "ephemeral": True,
                    },
                })
            elif msg.get("id") == 2:
                if "error" in msg:
                    print("THREAD_ERROR=" + str(msg["error"].get("message")))
                    return 2
                thread_id = msg.get("result", {}).get("thread", {}).get("id")
                if not thread_id:
                    print("THREAD_ID_MISSING")
                    return 2
                print("THREAD_STARTED=yes")
                send(proc, {
                    "id": 3, "method": "mcpServerStatus/list",
                    "params": {
                        "threadId": thread_id,
                        "serverName": SERVER,
                        "detail": "toolsAndAuthOnly",
                    },
                })
            elif msg.get("id") == 3:
                if "error" in msg:
                    print("MCP_STATUS_ERROR=" + str(msg["error"].get("message")))
                else:
                    print("MCP_STATUS_RECEIVED=yes")
                # The request is standalone (no language model generation).
                send(proc, {
                    "id": 4, "method": "mcpServer/tool/call",
                    "params": {
                        "threadId": thread_id,
                        "server": SERVER,
                        "tool": DEMO_TOOL_NAME if public_demo else "probe_confirmation",
                        "arguments": {},
                    },
                })
                pending_call = True
            elif msg.get("method") == "mcpServer/elicitation/request":
                params = msg.get("params", {})
                req = params.get("request", params)
                mode = req.get("mode") if isinstance(req, dict) else None
                print("ELICITATION_EVENT=yes")
                print("ELICITATION_MODE=" + str(mode))
                print("ELICITATION_SERVER_MATCH=" + str(params.get("serverName") == SERVER))
                elicitation_seen = True
                # The client automatically answers with NON-SECRET metadata.
                # No user response, API token, file write, or host GUI is involved.
                if msg.get("id") is not None:
                    send(proc, {
                        "id": msg["id"],
                        "result": {
                            "action": "accept",
                            "content": ({"demo_text": DEMO_MARKER} if public_demo else {
                                "destination": "config/.env.local",
                                "confirm": True,
                            }),
                        },
                    })
            elif msg.get("id") == 4:
                if "error" in msg:
                    print("TOOL_CALL_ERROR=" + str(msg["error"].get("message")))
                else:
                    result = json.dumps(msg.get("result", {}))
                    print("TOOL_CALL_RESULT=" + result[:500])
                    demo_marker_visible = DEMO_MARKER in result
                    tool_result_seen = True
                break
            elif "error" in msg and msg.get("id") is not None:
                print("RPC_ERROR_ID=" + str(msg["id"]))
        print("INIT_OK=" + str(init_ack))
        print("CALL_STARTED=" + str(pending_call))
        print("FORM_ROUTED=" + str(elicitation_seen))
        print("CALL_RETURNED=" + str(tool_result_seen))
        if public_demo:
            print("PUBLIC_DEMO_MARKER_IN_TOOL_RESULT=" + str(demo_marker_visible))
        return 0 if elicitation_seen and tool_result_seen and (not public_demo or demo_marker_visible) else 1
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=2)
        sel.close()


if __name__ == "__main__":
    sys.exit(run())
