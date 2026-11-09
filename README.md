# OTP Auth

Passwordless login by one-time email code. Django REST API, codes in Redis, emails via Celery.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Django](https://img.shields.io/badge/Django-6.1-092E20?logo=django&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white)
![Celery](https://img.shields.io/badge/Celery-5.6-37814A?logo=celery&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)

## Flow

```
POST /api/v1/auth/code/    {"email"}          → 202, code sent by Celery
POST /api/v1/auth/verify/  {"email", "code"}  → 200 {"token", "is_new"}
GET  /api/v1/auth/me/      Token <key>        → current user
```

No account yet — it is created on first successful login.

## Security details

- **Code is never stored in plain text** — Redis keeps an HMAC of it, so a cache dump doesn't let anyone log in.
- **Brute-force protection** — 5 attempts per code (atomic `INCR`, so parallel requests can't bypass it), then the code is burned.
- **Single use** — a code is deleted right after successful login.
- **Resend cooldown** — one code per 60 s per email (atomic `SET NX`), `429` with `Retry-After` otherwise.
- **Per-IP throttling** on top of per-email limits.
- **No account enumeration** — the same response for known and unknown emails.
- Email delivery retries with backoff if SMTP is temporarily down.

All limits are configurable via `.env` (`OTP_CODE_TTL`, `OTP_RESEND_COOLDOWN`, `OTP_MAX_ATTEMPTS`).

## Run

```bash
cp .env.example .env
docker compose up --build
```

Swagger: http://localhost:8000/api/v1/swagger/

By default emails are printed to the worker log: `docker compose logs -f celery`. Set `EMAIL_*` in `.env` for real SMTP.

## Tests

```bash
python manage.py test
```
