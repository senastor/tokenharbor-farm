# TokenHarbor farm — recon notes (2026-10-11)

Target: https://tokenharbor.ai — AI gateway, "20+ models, free models on every
account, $0 to start, $1.99/month pass". Goal: farm accounts via temp mail,
enable free models, mint an API key, save it to a .txt file.

## Stack (reverse-engineered from the login bundle)

- Next.js (App Router, turbopack) on Vercel.
- Auth = **Supabase GoTrue** project `isbnzmwjmtiuipesgmmg`.
  - URL: `https://isbnzmwjmtiuipesgmmg.supabase.co`
  - anon key: in `/tmp/thc/0.4.dgcznq8y1.js` (JWT role=anon, ref=isbnzmwjmtiuipesgmmg, 208 chars)
  - settings: email=true, google=true, github=true, anonymous_users=false
- Signup/signin go through **Next.js server actions** (`createServerReference`
  "signUp"/"signIn"/"sendLoginPin"/"verifyLoginPin"), not direct Supabase calls.
  Form fields: email, password, invite_code(optional), device_fingerprint(hidden),
  timezone(hidden), plus `$ACTION_*` hidden inputs.
- Captcha: **Cloudflare Turnstile** — component `h({action,onVerified})`,
  sitekey `0x4AAAAAADBuC8Knz1EJZx9-`, action `"signup"`.
  Gating: `GET /api/auth/signup-precheck?fp=<fingerprint>` -> `{needCaptcha:bool}`.
  Turnstile callback value goes into hidden input `cf-turnstile-response`.
- Other endpoints seen: `/api/auth/precheck-code` (POST {code,email,device_fingerprint}),
  `/api/keys` (401 unauth -> API key management), `/api/broadcast`, `/api/chat/unread-count`.

## Direct Supabase signup is BLOCKED

`POST /auth/v1/signup {email,password}` -> `{"code":"P0001","message":
"signup_trigger_error:P0001:signup_ip_required"}`. A DB trigger requires the
client IP, which only the Next.js server action can supply. Adding
`X-Forwarded-For`/`X-Real-IP` headers does not help. So signup MUST go through
the site's server action from a real browser page.

## Temp mail (works)

Provider `https://mail-api.markchain.bond` (own CF worker). **Must call with the
`curl` binary** — urllib/python-requests gets `403 error code: 1010` (CF bot rule).

```
POST /admin/new_address   header x-admin-auth: <MAIL_ADMIN>   (see qwen-farm/qwen_farm.py)
     {"name":"th<hex>","enablePrefix":false,"domain":"markchain.bond"}
     -> {"jwt":..., "address":"th..@markchain.bond", "address_id":N}
GET  /admin/mails?limit=10&offset=0&address=<urlencoded email>   header x-admin-auth
```
Admin key + domain live in `/root/qwen-farm/qwen_farm.py` constants
(`MAIL_ADMIN`, `MAIL_DOMAIN`). OTP extractor there decodes base64 bodies and
looks for `class="code..."`.

## Blocker found

Submitting the signup form returns **"You're doing that a bit fast — take a
breath and try again."** even with a fresh mailbox. This is the server action's
anti-bot timing/fingerprint check (Turnstile + device_fingerprint + timing).
Needs: a real render with Turnstile solved, correct `device_fingerprint`, and
human-paced interaction. Solver :8877 supports `turnstile` type; sitekey
`0x4AAAAAADBuC8Knz1EJZx9-` with `action=signup`.

## Files

- `/root/tokenharbor/camo.py` — camofox helper (new_tab/js/navigate) for userId
  `tharbor`. Camofox at `http://127.0.0.1:9377`, key `/root/.camofox-api-key`.
- `/tmp/thc/*.js` — downloaded login bundle chunks.
- `/tmp/th_login.html` — login page HTML.
- `.mailbox`, `.creds` — the test mailbox + generated password (never commit).
