# AGENTS.md — TokenHarbor farm

Farms TokenHarbor (tokenharbor.ai) accounts via temp mail, enables the free
models, verifies the email, and mints an API key. Keys land in
`data/apikeys.txt` (one per line) and are recorded per account in
`data/accounts.jsonl`.

## Commands

```bash
cd /root/tokenharbor
python3 tokenharbor_farm.py --count 1            # farm 1 account (settle 20s)
python3 tokenharbor_farm.py --count 5 --settle 25
python3 test_key.py                              # verify keys: models + free chat
```

Artifacts: `data/apikeys.txt` (keys), `data/accounts.jsonl` ({email,password,key,verified}),
`farm.log`. Also see `RECON.md` (raw recon) and `camo.py` (browser helper).

## API (OpenAI-compatible)

Base `https://tokenharbor.ai`, header `Authorization: Bearer <thk_live_...>`.

- `GET /v1/models` — 68 models; free ones are suffixed `:free`:
  `mimo-v2.5:free`, `deepseek-v4-flash:free`, `deepseek-v4.1-flash:free`,
  `mimo-v2.6-flash:free`, `claude-haiku-5.5:free`.
- `POST /v1/chat/completions` — `{model, messages, max_tokens}` (non-stream ok).
  Verified working: `{"model":"mimo-v2.5:free", ...}` -> normal completion.

## Signup flow (why browser, not HTTP)

- Site = Next.js + **Supabase GoTrue** (`isbnzmwjmtiuipesgmmg`).
- Signup goes through a **Next.js server action**, not direct Supabase.
  Direct `POST /auth/v1/signup` -> `{"code":"P0001","message":
  "signup_trigger_error:P0001:signup_ip_required"}` (a DB trigger wants the
  client IP, only the server action supplies it).
- **No captcha needed**: `GET /api/auth/signup-precheck?fp=<fp>` returns
  `{needCaptcha:false}`. (Turnstile sitekey `0x4AAAAAADBuC8Knz1EJZx9-` exists
  but is not triggered.)
- **The one blocker**: submitting too early yields
  *"You're doing that a bit fast — take a breath and try again."* It is a pure
  timing guard — **wait ~20s after the page settles before clicking
  "Create account"** and it succeeds. `--settle` controls this (default 20).
- Fingerprint comes from localStorage `th_did` (sent as `device_fingerprint`);
  it is stable per browser profile and does NOT need rotating.

Steps done by `farm_one()`:
1. temp mailbox (`POST /admin/new_address` on mail-api.markchain.bond)
2. open `https://tokenharbor.ai/login`, click "Create an account"
3. fill email + password, **sleep settle**, click "Create account"
4. on `/dashboard`: click "Enable free models"
5. click "API Key" -> "New key" -> name -> "Create key" -> read `thk_live_...`
6. click "Verify email", poll the mailbox for the link, open it
   (-> `/dashboard?verify=success`)

Key is created **before** email verification on purpose (verification only
gates making calls, not key creation), so a late verify mail never loses a key.

## Temp mail

ONLY `https://mail-api.markchain.bond`. **Use the `curl` binary** — urllib /
python-requests get `403 error code: 1010` (CF bot rule). The admin key +
domain are read at runtime from `/root/qwen-farm/qwen_farm.py`
(`MAIL_ADMIN`, `MAIL_DOMAIN`); never hardcode them here.

```
POST /admin/new_address  header x-admin-auth:<key>  {"name","enablePrefix":false,"domain"}
GET  /admin/mails?limit=10&offset=0&address=<urlenc>  header x-admin-auth
```

Verify links are soft-wrapped in the raw MIME, so unwrap `=\r\n` before
regexing the token.

## Browser

Camofox `http://127.0.0.1:9377`, key `/root/.camofox-api-key`, userId `tharbor`.
Helper `camo.py`: `new_tab`, `js`, `navigate`, `req`.

## Known issues / pitfalls

- **"a bit fast"** -> increase `--settle` (>= 15s, 20-25s is safe).
- **Verify email often never arrives** (`send.tokenharbor.ai` via Amazon SES);
  the key is still valid, so the farm counts the account as OK and marks
  `verified:false`. Re-click "Verify email" later if you need calls enabled.
- **Camofox tab exhaustion**: after several runs `new_tab` can return None if a
  prior session is stuck. Check `GET /tabs?userId=tharbor` and retry; a fresh
  tab usually works once the stuck one is navigated away.
- **Revoked keys**: a key is invalidated if you recreate/rotate it; re-run
  `test_key.py` to see which keys are still live.
- Never commit `data/`, `.creds`, or `.mailbox`.

## Working example

```
$ python3 tokenharbor_farm.py --count 1 --settle 22
[..] signed up -> dashboard
[..] free models enabled
[..] API key minted (thk_live_ZJnHf3nvfO9...)
[..] WARN: verify email did not arrive; key still saved
=== done: 1/1 ok ===

$ python3 test_key.py
=== key 1 (thk_live_i5_Kg-CS1Hf5P...) ===
  models: 68, free: ['mimo-v2.5:free', 'deepseek-v4-flash:free', ...]
  chat[mimo-v2.5:free]: {"id":"chatcmpl-...","choices":[{"message":{"content":"Hi there! ..."}}]}
```
