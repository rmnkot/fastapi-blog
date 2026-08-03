# Architecture & Backend Review — FastAPI Blog

**Date:** 2026-08-03
**Scope:** Full codebase — `main.py`, `async_db.py`, `models.py`, `schemas.py`, `auth.py`, `routers/`, `email_utils.py`, `image_utils.py`, `config.py`, templates.
**Context:** This is a learning project. The review is intentionally thorough — every point below is something to *learn from*, not criticism. The fundamentals (argon2 hashing, hashed reset tokens, ownership checks, eager loading) are already above average for a tutorial project. Prioritize the **High** section, then work down.

---

## High severity

### 1. `blog.db` is committed to git with real user PII
`git ls-files` shows `blog.db` (plus uploaded profile images) is tracked. It contains real emails (`coreymschafer@gmail.com`, …) and argon2 password hashes, readable by anyone with repo access.

**Lesson:** Never commit runtime data. Add to `.gitignore` and purge from history (e.g. `git filter-repo`).

```gitignore
blog.db
media/
```

### 2. No rate limiting on auth endpoints
`POST /api/users/token`, `/forgot-password`, `/reset-password`, and `POST /api/users` have no throttling → brute-force login and mailbox-spam (forgot-password will send a reset email to any address on demand).

**Lesson:** Auth endpoints are the first thing attackers target. Slow them down (e.g. `slowapi`, Redis-based counters, or IP + account locks).

**Lesson:** Always unit-test computed user-facing messages.

```python
f"Maximum size is {settings.max_upload_size_bytes // (1024 * 1024)}MB"
```

### 4. Image upload robustness
`routers/users.py:406-419`, `image_utils.py`:
- The entire file is read into memory before the size check; cap by `Content-Length` or stream.
- No pixel-dimension guard → a *decompression bomb* (small file, huge dimensions) exhausts memory during resize.
- Only `UnidentifiedImageError` is caught; `DecompressionBombError` and `OSError` (truncated file) propagate as 500s.

**Lesson:** Never trust uploads. Bound both bytes *and* pixels; catch the full family of image-decoding exceptions.

### 5. JWT in `localStorage` + no CSP
Autoescape (`{{ }}`) and `textContent` mitigate XSS, but the CSP header is commented out (`templates/layout.html:61`) and the token lives in `localStorage`. Any script injection steals the session.

**Lesson:** Defense-in-depth. Enable CSP and/or serve the token in an httpOnly cookie. `localStorage` is fine for a learning project, but know the trade-off.

---

## Medium severity

### 6. No migrations
Schema is `create_all` at startup (`main.py:20`). There is already one schema evolution (auth tables) with no versioning story.

**Lesson:** Alembic exists exactly for this — start it early, it's much harder to retrofit.

### 7. Zero tests
No test suite covers auth, ownership, or reset-token flows.

**Lesson:** The auth flows are the most security-critical and the most testable. `pytest` + `httpx.AsyncClient` + a test DB would pay off immediately.

### 8. TOCTOU on uniqueness checks
`routers/users.py:232-250`, `284-307` — check-then-insert races on `username`/`email` surface as an unhandled `IntegrityError` → 500. The case-sensitive unique index also allows `"Bob"`/`"bob"` to diverge under a race.

**Lesson:** Make the DB the source of truth (unique constraint + `IntegrityError` handler), or use case-insensitive/functional indexes.

### 9. `update_user` self-collision bug
`routers/users.py:284`, `297` — changing only the *case* of your own username/email (`Bob` → `bob`) hits the uniqueness lookup, finds your own record, and returns 400 "already exists". The comparison is case-sensitive but the check is case-insensitive.

### 10. No max length on `password` / `content`
`UserCreateSchema.password` and `PostBaseSchema.content` only set `min_length`. A multi-MB password forces an expensive argon2 hash (CPU DoS).

**Lesson:** Always cap password length (e.g. 128). Long-password handling is a real attack vector.

### 11. Orphaned image files
`routers/users.py:421-427` — the new image is written before commit (orphan if commit fails); the old image is deleted after commit (orphan if delete fails).

**Lesson:** Write-then-commit, commit-then-delete is the right shape; the failure windows are the interesting part. A cleanup job or temp dir is the "real world" answer.

### 12. `tokenUrl` missing leading slash
`auth.py:17` — `OAuth2PasswordBearer(tokenUrl="api/users/token")` produces a broken relative link in OpenAPI docs.

**Lesson:** `tokenUrl` needs to be `/api/users/token`.

### 13. Email delivery is fire-and-forget
`BackgroundTasks` sends the reset email with no retry/logging; failures are silent and the user never gets the email.

**Lesson:** Background tasks are fine for a learning project; production needs a queue (Celery/ARQ) or at least error capture + retry.

---

## Low / nits

- **`ruff check .` fails** on the deprecated `main_sync.py:291` (`SIM202`) — the documented lint gate can't pass without fixing or excluding that file.
- **`except TypeError, ValueError:`** (`auth.py:84`) uses PEP 758 unparenthesized except tuples — valid here because the project requires Python 3.14+ (`requires-python = ">=3.14"`). Not a bug: Ruff's formatter (preview) strips the parens, so `except (TypeError, ValueError):` gets normalized back to the unparenthesized form on format. The only real caveat is it *looks* like Python 2 syntax and would break on <3.14 — neither applies to this project.
- **No logging middleware** — server-side errors and attacks aren't recorded.
- **Pagination is SSR-first-page + API "load more", not missing** (`routers/templates.py`) — the template routes deliberately don't paginate themselves. The server renders the first page and passes `has_more` + `limit` as a first-load signal; the frontend then takes over pagination via the paginated API endpoints (`GET /api/posts` and `GET /api/users/{user_id}/posts`, both accepting `skip`/`limit` and returning `has_more` in `PaginatedPostResponseSchema`). Minor nit: the template computes `has_more` as `len(posts) < total` while the API uses `skip + len(posts) < total` — equivalent on the first page (skip = 0), but keep them in sync if offsets ever change.
- **`docs/status_codes.md`** omits 403 and the 202 forgot-password code.
- **Duplicate `Jinja2Templates`** instances in `templates.py` and `email_utils.py`.
- **CWD-dependent paths** for `static/`, `media/`, `templates/` — breaks if launched from another directory; use `Path(__file__).parent`.
- **No JWT `iat`/`jti`/`aud` claims**; logout is client-side only (token stays valid for its full 30 min).

---

## What's done well (worth keeping as a baseline)

- Argon2 password hashing via `pwdlib`.
- Reset tokens stored as SHA-256 hashes, with expiry and single-use semantics.
- Generic anti-enumeration messages on forgot-password.
- `Referrer-Policy: no-referrer` on the reset page.
- `selectinload` everywhere — no N+1 queries.
- Ownership checks returning 403; 401s carry `WWW-Authenticate: Bearer`.
- `from_attributes=True` schemas, response schemas returned consistently.
- `SecretStr` for secrets; `.env` correctly gitignored.
