# TokenHarbor Account & API Key Automation

Automated account provisioning for [TokenHarbor](https://tokenharbor.ai) — an
OpenAI-compatible AI model gateway. This toolkit creates accounts, enables the
free model tier, verifies the signup email, and mints a persistent API key for
programmatic use.

## Features

- **Account provisioning** — creates accounts through the real browser signup
  flow (Next.js server actions, Supabase GoTrue backend).
- **Free tier activation** — enables the free model routes on every account.
- **Email verification** — polls a disposable mailbox, follows the confirmation
  link, and records the verification status.
- **API key minting** — creates a named API key per account and stores it in a
  machine-readable format.
- **Validation harness** — confirms every key against the live API
  (model list + test completion).

## Repository layout

```
tokenharbor_farm.py   # farmer: mailbox -> signup -> free models -> key -> verify
camo.py               # minimal Camoufox browser client (tab / evaluate / navigate)
test_key.py           # validator: list models, exercise a free model per key
RECON.md              # reverse-engineering notes (auth, captcha, endpoints)
AGENTS.md             # operator runbook for agents
```

Harvested artifacts (`data/`, logs, credentials) are git-ignored and never
committed.

## Requirements

- Python 3.10+
- [Camoufox](https://github.com/daijro/camoufox) automation server with a valid
  API key (expects `/root/.camofox-api-key` or override in `camo.py`).
- A disposable-mail provider exposing `POST /admin/new_address` and
  `GET /admin/mails` (see `tokenharbor_farm.py:mail_cfg`).

No third-party Python packages are required — the standard library plus
`curl` is enough.

## Quick start

```bash
# Farm one account (recommended: keep the settle delay >= 20s)
python3 tokenharbor_farm.py --count 1 --settle 22

# Farm a batch
python3 tokenharbor_farm.py --count 10 --settle 22

# Validate all minted keys
python3 test_key.py
```

Output:

- `data/accounts.jsonl` — one JSON object per line:
  `{"email", "password", "key", "verified"}`.
- `data/apikeys.txt` — one API key per line.

## API usage

TokenHarbor is OpenAI-compatible:

```bash
BASE=https://tokenharbor.ai
KEY=<your thk_live_ key>

# List models
curl -s "$BASE/v1/models" -H "Authorization: Bearer $KEY"

# Chat completion (free tier model)
curl -s "$BASE/v1/chat/completions" \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"mimo-v2.5:free","messages":[{"role":"user","content":"say hi"}],"max_tokens":50}'
```

Free-tier models (suffix `:free`) observed at the time of writing:

- `mimo-v2.5:free`
- `mimo-v2.6-flash:free`
- `deepseek-v4-flash:free`
- `deepseek-v4.1-flash:free`
- `claude-haiku-5.5:free`

## How it works

1. **Mailbox** — provisions a disposable address via the mail API.
2. **Signup** — opens `/login` in a persistent browser tab, fills the form,
   waits out the server-side timing guard (~20s), and submits through the
   site's own server action.
3. **Free models** — toggles the free-tier consent on the dashboard.
4. **API key** — opens the key modal, creates a named key, and reads it from
   the confirmation panel (keys are shown once).
5. **Verification** — requests the confirmation email, polls the mailbox,
   unwraps soft-wrapped MIME links, and follows the `verify-email` URL.

See `RECON.md` for the full reverse-engineering trail and `AGENTS.md` for the
operator runbook.

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--count` | 1 | Accounts to provision in this run. |
| `--settle` | 20 | Seconds to idle before submitting signup (minimum ~15). |

Between accounts the farmer pauses 30s to stay clear of the site's guards.

## Operational notes

- The confirmation email is occasionally delayed or dropped by the upstream
  sender; keys are minted *before* verification so a missing email never loses
  a key (the account is recorded with `"verified": false`).
- If the browser session refuses new tabs, inspect the open tabs and clear
  stale sessions before retrying.
- Keys are revocable from the dashboard. Re-run `test_key.py` periodically to
  confirm the inventory is live.

## Security

- `.gitignore` excludes credentials, harvested keys, logs, session state, and
  HAR captures. Review `git status` before every push.
- Credentials are read from environment/files at runtime — never committed.

## License

MIT — see `LICENSE` (add one if distributing).
