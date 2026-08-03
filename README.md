# FastAPI Blog

A feature-complete blog built with **FastAPI** — server-rendered HTML pages **and** a JSON API, JWT authentication, password reset by email, and profile picture uploads.

This is a learning project originally based on the [Corey Schafer FastAPI tutorial](https://youtu.be/7AMjmCTumuo?si=ExB5Vx94oH4kdO7a), extended well beyond the tutorial with an async SQLAlchemy stack, auth flows, and image handling.

## Features

- **Async-first** FastAPI app (Python 3.14+) with SQLAlchemy 2.0 async ORM on SQLite (`aiosqlite`)
- **Authentication** — JWT access tokens + argon2 password hashing (`pwdlib`), OAuth2 `Bearer` flow
- **Password management** — change password; forgot / reset password by email (hashed single-use reset tokens, sent via `aiosmtplib` as a background task)
- **Posts** — create / read / update / delete with ownership checks and pagination
- **Profiles** — profile pictures (upload, crop/resize to 300×300, delete) processed with Pillow
- **Server-rendered pages** — Jinja2 templates (home, post, user posts, account, login, register, forgot/reset password)
- **JSON API** — `/api/users`, `/api/posts`, with interactive docs at `/docs`
- **Security-minded details** — case-insensitive uniqueness lookups, generic error messages (no email enumeration), ownership checks returning 403

## Tech stack

| Layer | Library |
| --- | --- |
| Framework | FastAPI (`uvicorn`/`fastapi dev`) |
| ORM | SQLAlchemy 2.0 (async) + `aiosqlite` |
| Validation | Pydantic v2 |
| Auth | PyJWT, `pwdlib[argon2]`, FastAPI security |
| Email | `aiosmtplib` |
| Images | Pillow |
| Templates | Jinja2 |
| Config | `pydantic-settings` (`.env`) |
| Tooling | `uv`, Ruff, Pyright |

## Requirements

- Python **3.14+**
- [`uv`](https://docs.astral.sh/uv/) (package manager)

## Getting started

1. **Install dependencies**

   ```bash
   uv sync
   ```

2. **Configure environment**

   ```bash
   cp .env.example .env
   ```

   Fill in `.env` — at minimum `SECRET_KEY`. See [Configuration](#configuration).

3. **Run the dev server**

   ```bash
   uv run fastapi dev
   ```

   Database tables are created automatically on startup (`blog.db`). Then open:

   - App: <http://localhost:8000>
   - Interactive API docs (Swagger UI): <http://localhost:8000/docs>

4. **(Optional) Seed sample data**

   ```bash
   uv run python populate_db.py
   ```

   Creates demo users and posts (with profile pictures from `populate_images/`). **Note:** this clears existing data first.

## Configuration

All settings are read from `.env` (see `.env.example` and `config.py`):

| Variable | Default | Description |
| --- | --- | --- |
| `SECRET_KEY` | *(required)* | JWT signing secret — use a long random value |
| `ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | JWT access-token lifetime |
| `RESET_TOKEN_EXPIRE_MINUTES` | `60` | Password-reset link lifetime |
| `POST_PER_PAGE` | `5` | Default posts per page |
| `MAX_UPLOAD_SIZE_BYTES` | `5242880` (5 MB) | Max profile-picture upload size |
| `MAIL_SERVER` | `localhost` | SMTP server for reset email |
| `MAIL_PORT` | `587` | SMTP port |
| `MAIL_USERNAME` / `MAIL_PASSWORD` | *(empty)* | SMTP credentials |
| `MAIL_FROM` | `noreply@example.com` | Sender address |
| `MAIL_USE_TLS` | `true` | Use STARTTLS |
| `FRONTEND_URL` | `http://localhost:8000` | Base URL used in reset links |

> For local email testing without a real SMTP server, point `MAIL_SERVER`/`MAIL_PORT` at a tool like [MailHog](https://github.com/mailhog/MailHog) or an `aiosmtpd` instance.

## API

Routers live in `routers/`. All API paths return JSON and are documented in `/docs`. Login is by **email** + password (submitted to `/api/users/token` as an OAuth2 password form).

### `/api/users`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `POST` | `/api/users` | – | Register a user |
| `POST` | `/api/users/token` | – | Login → JWT access token |
| `GET` | `/api/users/me` | ✅ | Current user (includes email) |
| `GET` | `/api/users/{id}` | – | Public user profile |
| `PATCH` | `/api/users/{id}` | ✅ | Update own username/email |
| `DELETE` | `/api/users/{id}` | ✅ | Delete own account |
| `GET` | `/api/users/{id}/posts` | – | A user's posts (paginated) |
| `PATCH` | `/api/users/{id}/picture` | ✅ | Upload own profile picture |
| `DELETE` | `/api/users/{id}/picture` | ✅ | Remove own profile picture |
| `PATCH` | `/api/users/me/password` | ✅ | Change own password |
| `POST` | `/api/users/forgot-password` | – | Request a password-reset email (returns `202`) |
| `POST` | `/api/users/reset-password` | – | Reset password with email token |

### `/api/posts`

| Method | Path | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/api/posts` | – | List posts (paginated: `skip`, `limit`) |
| `GET` | `/api/posts/{id}` | – | Get a post |
| `POST` | `/api/posts` | ✅ | Create a post |
| `PUT` | `/api/posts/{id}` | ✅ | Replace a post (own posts only) |
| `PATCH` | `/api/posts/{id}` | ✅ | Update a post (own posts only) |
| `DELETE` | `/api/posts/{id}` | ✅ | Delete a post (own posts only) |

See [docs/status_codes.md](docs/status_codes.md) for the HTTP status code conventions used across the API.

## Project structure

```
main.py          App entrypoint, router mounting, error handlers
async_db.py      Async engine, session factory, declarative Base
models.py        SQLAlchemy models (User, Post, PasswordResetToken)
schemas.py       Pydantic schemas (Base / Create / Update / Response)
auth.py          JWT + argon2, current-user dependency
config.py        pydantic-settings configuration (.env)
email_utils.py   Password-reset email sending (aiosmtplib)
image_utils.py   Profile-picture processing (Pillow)
populate_db.py   Seed script (demo users + 44 posts + images)
routers/
  templates.py   Server-rendered HTML pages (Jinja2)
  users.py       /api/users
  posts.py       /api/posts
templates/       Jinja2 templates (incl. email/ for reset mail)
static/          CSS, JS, icons
media/           Uploaded profile pictures
docs/            Project docs (status codes, architecture review)
```

> `main_sync.py` and `sync_db.py` are deprecated and kept for reference only — all active code is async.

## Development

- **Lint:** `uv run ruff check .`
- **Type check:** `uv run pyright` (`typeCheckingMode = "standard"`)

## Acknowledgements

Built as a learning project following the [Corey Schafer FastAPI tutorial](https://youtu.be/7AMjmCTumuo?si=ExB5Vx94oH4kdO7a), extended with JWT auth, password reset by email, profile pictures, and an async SQLAlchemy stack.
