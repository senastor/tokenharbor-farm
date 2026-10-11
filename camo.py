#!/usr/bin/env python3
"""Minimal camofox client for the TokenHarbor farm."""
import json
import subprocess
import urllib.parse

CAMO = "http://127.0.0.1:9377"


def _key():
    return open("/root/.camofox-api-key").read().strip()


def req(method, path, body=None, timeout=60):
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", method, CAMO + path,
           "-H", "Authorization: Bearer " + _key(),
           "-H", "Content-Type: application/json"]
    if body is not None:
        cmd += ["-d", json.dumps(body)]
    out = subprocess.run(cmd, capture_output=True, text=True).stdout
    try:
        return json.loads(out)
    except Exception:
        return {"raw": out[:300]}


def new_tab(user, session, url):
    r = req("POST", "/tabs", {"userId": user, "sessionKey": session, "url": url})
    return r.get("tabId")


def js(tab, user, expr, timeout=90):
    r = req("POST", f"/tabs/{tab}/evaluate",
            {"userId": user, "expression": expr}, timeout=timeout)
    return r.get("result")


def navigate(tab, user, url):
    return req("POST", f"/tabs/{tab}/navigate", {"userId": user, "url": url})
