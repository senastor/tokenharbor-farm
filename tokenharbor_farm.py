#!/usr/bin/env python3
"""TokenHarbor account farm — signup (temp mail) -> enable free models ->
verify email -> mint API key, all via the real browser page (camofox).

Why the browser: signup goes through a Next.js server action that rejects
direct Supabase calls ("signup_ip_required") and rate-limits fast submits with
"You're doing that a bit fast — take a breath and try again." The guard is
purely timing-based: waiting ~20s after the page settles before submitting
succeeds. No Turnstile is required (signup-precheck returns needCaptcha:false).

Flow per account:
  1. create a temp mailbox at mail-api.markchain.bond (curl binary — urllib
     gets CF 403 code 1010)
  2. open https://tokenharbor.ai/login, click "Create an account"
  3. fill email + password, wait SETTLE_SECONDS, click "Create account"
  4. once on /dashboard: click "Enable free models"
  5. click "Verify email", poll the mailbox for the verify link, open it
     (-> /dashboard?verify=success)
  6. open the API key modal, create a key, read it from the page
  7. append {email, password, key} to data/accounts.jsonl and the key to
     data/apikeys.txt

Usage:
  python3 tokenharbor_farm.py --count 1
  python3 tokenharbor_farm.py --count 5 --settle 22
"""
import argparse
import json
import os
import re
import secrets
import subprocess
import sys
import time
import urllib.parse

import camo

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
LOG = os.path.join(HERE, "farm.log")
MAIL_API = "https://mail-api.markchain.bond"
USER = "tharbor"

# read the mail admin key + domain from the existing qwen-farm constants
def mail_cfg():
    src = open("/root/qwen-farm/qwen_farm.py").read()
    admin = re.search(r'MAIL_ADMIN\s*=\s*"([^"]+)"', src).group(1)
    domain = re.search(r'MAIL_DOMAIN\s*=\s*"([^"]+)"', src).group(1)
    return admin, domain


def log(m):
    line = "[%s] %s" % (time.strftime("%Y-%m-%d %H:%M:%S"), m)
    print(line, flush=True)
    try:
        open(LOG, "a").write(line + "\n")
    except Exception:
        pass


def curl(url, method="GET", headers=None, data=None, timeout=25):
    cmd = ["curl", "-sS", "-m", str(timeout), "-X", method, url,
           "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)"]
    for k, v in (headers or {}).items():
        cmd += ["-H", f"{k}: {v}"]
    if data is not None:
        cmd += ["-H", "Content-Type: application/json", "-d", json.dumps(data)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout


def new_mailbox(admin, domain):
    name = "th" + secrets.token_hex(5)
    out = curl(f"{MAIL_API}/admin/new_address", "POST",
               {"x-admin-auth": admin},
               {"name": name, "enablePrefix": False, "domain": domain})
    return json.loads(out)["address"]


def poll_verify_link(email, admin, timeout=90, interval=10):
    q = urllib.parse.quote(email)
    deadline = time.time() + timeout
    import quopri
    while time.time() < deadline:
        out = curl(f"{MAIL_API}/admin/mails?limit=5&offset=0&address={q}",
                   headers={"x-admin-auth": admin})
        try:
            mails = json.loads(out).get("results", [])
        except Exception:
            mails = []
        for m in mails:
            raw = m.get("raw", "")
            qp = quopri.decodestring(raw.encode()).decode("utf-8", "ignore")
            for src in (raw, qp):
                # links may be soft-wrapped with "=\r\n"; unwrap first
                flat = src.replace("=\r\n", "").replace("=\n", "")
                for link in re.findall(
                        r'https://tokenharbor\.ai/verify-email\?token=[A-Za-z0-9_\-\.]+',
                        flat):
                    return link
        time.sleep(interval)
    return None


def fill(tab, name, val):
    camo.js(tab, USER, "(function(){var el=document.querySelector('input[name=%s]');"
            "var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            "s.call(el,%s);el.dispatchEvent(new Event('input',{bubbles:true}));return el.value.slice(0,24);})()"
            % (name, json.dumps(val)))


def click(tab, label_re):
    return camo.js(tab, USER,
                   "(function(){var b=[...document.querySelectorAll('button,a')]"
                   ".filter(function(x){return /%s/i.test(x.innerText);});"
                   "b.forEach(function(x){x.click();});return 'clicked '+b.length;})()" % label_re)


def body(tab):
    return camo.js(tab, USER, "document.body.innerText") or ""


def farm_one(settle, admin, domain):
    email = new_mailbox(admin, domain)
    pw = "Th" + secrets.token_urlsafe(14)
    log(f"[{email}] mailbox created")
    tab = camo.new_tab(USER, "th-" + secrets.token_hex(4), "https://tokenharbor.ai/login")
    if not tab:
        log(f"[{email}] FAIL: could not open tab")
        return None
    time.sleep(9)
    click(tab, "Create an account")
    time.sleep(5)
    fill(tab, "email", email)
    time.sleep(2.5)
    fill(tab, "password", pw)
    log(f"[{email}] form filled, settling {settle}s (anti 'a bit fast' guard)")
    time.sleep(settle)
    click(tab, "^Create account$")
    time.sleep(10)
    if "a bit fast" in body(tab):
        log(f"[{email}] FAIL: rate-limited ('a bit fast'); increase --settle")
        return None
    if "/dashboard" not in camo.js(tab, USER, "location.href"):
        log(f"[{email}] FAIL: not on dashboard; body={body(tab)[:150]}")
        return None
    log(f"[{email}] signed up -> dashboard")

    click(tab, "Enable free models")
    time.sleep(4)
    log(f"[{email}] free models enabled")

    # create the API key FIRST (email verification only gates making calls,
    # not key creation), so a late verify mail never loses the key
    # open the key section, then the create modal
    click(tab, "API Key")
    time.sleep(3)
    clicked = click(tab, "^New key$")
    log(f"[{email}] new-key click: {clicked}")
    time.sleep(3)
    if "Create key" not in body(tab):
        # fallback: the overview button "Create a key" also opens the modal
        click(tab, "Create a key")
        time.sleep(3)
    camo.js(tab, USER, "(function(){var el=document.querySelector('input[placeholder*=\"Cursor\"]');"
            "if(!el){var i=document.querySelector('[role=dialog] input, form input');el=i;}"
            "if(!el)return 'nf';var s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;"
            "s.call(el,'farm');el.dispatchEvent(new Event('input',{bubbles:true}));return 'ok';})()")
    time.sleep(1.5)
    camo.js(tab, USER, "(function(){var b=[...document.querySelectorAll('button')]"
            ".find(function(x){return x.innerText.trim()==='Create key';});if(b){b.click();return 'ok';}return 'nf';})()")
    time.sleep(6)
    m = re.search(r"thk_live_[A-Za-z0-9_\-]+", body(tab))
    if not m:
        log(f"[{email}] FAIL: no key found in page; body={body(tab)[:250]}")
        return None
    key = m.group(0)
    log(f"[{email}] API key minted ({key[:20]}...)")

    # then verify the email
    click(tab, "Verify email")
    time.sleep(4)
    link = poll_verify_link(email, admin)
    verified = False
    if link:
        camo.navigate(tab, USER, link)
        time.sleep(6)
        verified = "/dashboard" in camo.js(tab, USER, "location.href")
        log(f"[{email}] email verified={verified}")
    else:
        log(f"[{email}] WARN: verify email did not arrive; key still saved")

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "accounts.jsonl"), "a") as f:
        f.write(json.dumps({"email": email, "password": pw, "key": key,
                            "verified": verified}) + "\n")
    with open(os.path.join(DATA, "apikeys.txt"), "a") as f:
        f.write(key + "\n")
    os.chmod(os.path.join(DATA, "apikeys.txt"), 0o600)
    return {"email": email, "password": pw, "key": key, "verified": verified}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--settle", type=int, default=20,
                    help="seconds to wait before submitting signup (min ~15)")
    a = ap.parse_args()
    admin, domain = mail_cfg()
    log(f"=== TokenHarbor farm: {a.count} account(s), settle={a.settle}s ===")
    ok = 0
    for i in range(a.count):
        log(f"--- account {i+1}/{a.count} ---")
        try:
            r = farm_one(a.settle, admin, domain)
            if r:
                ok += 1
        except Exception as e:
            log(f"error: {e}")
        if i < a.count - 1:
            time.sleep(30)
    log(f"=== done: {ok}/{a.count} ok ===")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
