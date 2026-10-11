#!/usr/bin/env python3
"""Debug: pull the verify link for one mailbox."""
import json, re, quopri, subprocess, sys, urllib.parse

email = sys.argv[1]
src = open("/root/qwen-farm/qwen_farm.py").read()
ADMIN = re.search(r'MAIL_ADMIN\s*=\s*"([^"]+)"', src).group(1)
q = urllib.parse.quote(email)
url = f"https://mail-api.markchain.bond/admin/mails?limit=5&offset=0&address={q}"
out = subprocess.run(["curl", "-sS", "-m", "25", "-X", "GET", url,
                      "-H", "User-Agent: Mozilla/5.0", "-H", f"x-admin-auth: {ADMIN}"],
                     capture_output=True, text=True).stdout
d = json.loads(out)
print("mails:", len(d.get("results", [])))
for m in d.get("results", []):
    raw = m.get("raw", "")
    qp = quopri.decodestring(raw.encode()).decode("utf-8", "ignore")
    print("subject:", m.get("subject"))
    for src2, nm in [(raw, "raw"), (qp, "qp")]:
        links = re.findall(r"https://tokenharbor\.ai/verify-email\?token=[^\s\"'<>]+", src2)
        for l in links:
            print(nm, "LINK:", l)
