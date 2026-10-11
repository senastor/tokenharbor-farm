#!/usr/bin/env python3
"""Test TokenHarbor API keys: list models + one free chat completion."""
import json
import subprocess
import sys

BASE = "https://tokenharbor.ai"

def curl(url, headers=None, data=None):
    cmd = ["curl", "-sS", "-m", "40", url]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout

keys = [l.strip() for l in open("/root/tokenharbor/data/apikeys.txt") if l.strip()]
for i, k in enumerate(keys):
    print(f"=== key {i+1} ({k[:22]}...) ===")
    out = curl(f"{BASE}/v1/models", {"Authorization": "Bearer " + k})
    try:
        d = json.loads(out)
    except Exception:
        print("  not json:", out[:120]); continue
    if "error" in d:
        print("  ERROR:", d["error"]); continue
    models = d.get("data", [])
    free = [m["id"] for m in models
            if m.get("pricing", {}).get("input_usd_per_1m", 1) == 0
            and m.get("pricing", {}).get("output_usd_per_1m", 1) == 0]
    print(f"  models: {len(models)}, free: {free[:8]}")
    # try a free chat
    target = free[0] if free else (models[0]["id"] if models else None)
    if target:
        r = curl(f"{BASE}/v1/chat/completions", {"Authorization": "Bearer " + k},
                 {"model": target, "messages": [{"role": "user", "content": "say hi"}],
                  "max_tokens": 20})
        print(f"  chat[{target}]:", r[:200])
