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
| Testing | `pytest`, `anyio`, `moto` |
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
| `TEST_POSTGRES_DB` | `test_blog_db` | Test DB name (created by Docker init script; see [Docker setup](#-local-database-setup-postgresql-18)) |

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
tests/           Test suite (pytest + anyio; uses the test DB & moto S3)
docker/
  initdb/        Postgres init scripts (auto-create the test DB on first boot)
```

> `main_sync.py` and `sync_db.py` are deprecated and kept for reference only — all active code is async.

## Development

- **Run tests:** `uv run pytest` (or a single file, e.g. `uv run pytest tests/test_posts.py`)
- **Lint:** `uv run ruff check .`
- **Type check:** `uv run pyright` (`typeCheckingMode = "standard"`)

> Tests run against PostgreSQL, so the [Docker database](#-local-database-setup-postgresql-18) must be up — the suite connects to `test_blog_db` (auto-created on first boot, see section 5 above) and mocks S3 with `moto`.

## Acknowledgements

Built as a learning project following the [Corey Schafer FastAPI tutorial](https://youtu.be/7AMjmCTumuo?si=ExB5Vx94oH4kdO7a), extended with JWT auth, password reset by email, profile pictures, and an async SQLAlchemy stack.

## 🐳 Local Database Setup (PostgreSQL 18)

This project uses Docker Compose to run a local, completely isolated instance of PostgreSQL 18. This setup runs natively on Apple Silicon (M1/M2/M3/M4/M5) and won't pollute your host operating system.

### 🛠 Prerequisites
* [Docker Desktop](https://docker.com) installed and actively running in your menu bar.
* [DBeaver](https://dbeaver.io) or any other database GUI tool.

### 🔑 Connection Credentials

Values are read from the git-ignored `.env` file; `docker-compose.yml` falls back to the defaults below if a variable is unset. Override any of them in `.env`, then recreate the container with `docker compose up -d`.

| Setting | Default | Variable (in `.env`) |
| --- | --- | --- |
| Host | `localhost` | – |
| Port | `5432` | `POSTGRES_PORT` |
| Database Name | `blog_db` | `POSTGRES_DB` |
| Username | `blog_user` | `POSTGRES_USER` |
| Password | `password` | `POSTGRES_PASSWORD` |

> 💡 `DATABASE_URL` in `.env` is derived automatically from the `POSTGRES_*` variables (pydantic-settings expands the `${VAR}` references), so there's only one place to change credentials.

---

### 🚀 Important Commands

Always run these commands from the root directory of the project (where the `docker-compose.yml` file is located).

#### 1. Daily Start
To start the database container in the background (detached mode):
```bash
docker compose up -d
```
*Note: Since the configuration includes `restart: unless-stopped`, the container will automatically wake up whenever you open Docker Desktop in the morning. Currently commented*

#### 2. Daily Stop (Recommended)
You **do not** need to type any commands to stop your database daily. Simply **Quit Docker Desktop** from your macOS top menu bar. 
* This safely freezes your container's current state.
* It instantly releases 100% of CPU and RAM resources back to your Mac.

#### 3. Maintenance Stop (Switching Projects)
If you need to switch to another project using the same port (`5432`), completely clear the active containers, or update the `docker-compose.yml` file:
```bash
docker compose down
```
*This removes the temporary container sandbox, but **leaves all your tables and data completely untouched** inside the hidden volume.*

#### 4. Complete Reset (Wipe All Data)
If you want to completely erase the database, drop all tables, and start from a blank canvas:
```bash
docker compose down -v
```
⚠️ **Warning:** The `-v` (volumes) flag permanently deletes your local data volume. This action cannot be undone.

#### 5. Test Database (Auto-Created on First Boot)

On a fresh (empty) data volume, `docker/initdb/01-create-test-db.sh` runs automatically on the container's first boot and creates the test database (`test_blog_db`, configurable via `TEST_POSTGRES_DB` in `.env`). The test suite (`tests/`) connects to it directly.

⚠️ **The script must be executable.** The Postgres entrypoint executes scripts in `/docker-entrypoint-initdb.d` directly; if the file lacks the execute bit, the container fails to start with exit code `126` ("Permission denied"). The executable bit is **not tracked by git**, so after a fresh clone re-apply it before the first boot:

```bash
chmod +x docker/initdb/01-create-test-db.sh
docker compose down -v   # init scripts only run on an empty volume
docker compose up -d
```

#### 6. Check Database Status & Logs
If you cannot connect via DBeaver, use these commands to debug:
```bash
# Check if the container is running (should show Status "Up")
docker ps

# View the real-time startup logs or error messages from PostgreSQL container
docker logs postgres_dev
```

#### 7. Updating PostgreSQL 18 Image
If a new minor patch or security update is released for PostgreSQL 18, you can pull the latest image and recreate your container without losing data by running:
```bash
docker compose pull
docker compose up -d
```

#### 8. PostgreSQL CLI (psql)

Open a shell inside the running container and connect as `blog_user` to the `blog_db` database:

```bash
docker exec -it postgres_dev psql -U blog_user -d blog_db
```

Useful psql commands once connected:

```sql
\l                  -- list all databases
\dt                 -- list all tables in the current schema
\d posts            -- show columns, types and constraints of the posts table
\d+ posts           -- same, plus sizes, stats and indexes
\du                 -- list database roles (users)
\x                  -- toggle expanded output for wide rows
\q                  -- exit psql
```

Some handy queries against the blog schema (tables come from `models.py`: `users`, `posts`, `password_reset_tokens`):

```sql
SELECT id, title, likes FROM posts;
SELECT id, username, email FROM users;
SELECT COUNT(*) FROM posts WHERE likes > 0;
SELECT user_id, expires_at FROM password_reset_tokens;
```

#### 9. Alembic Migrations

Alembic reads the app's `DATABASE_URL` from `.env` (see `alembic/env.py`), so it always targets whichever database the app is configured to use — SQLite or PostgreSQL.

```bash
uv run alembic revision --autogenerate -m "describe change"   # generate a migration from model changes
uv run alembic upgrade head                                    # apply all pending migrations
uv run alembic upgrade +1                                      # apply just the next migration
uv run alembic downgrade -1                                    # roll back the latest migration
uv run alembic downgrade base                                  # roll back everything
uv run alembic current                                         # show which migration the DB is on (e.g. f98e5ac736e3 (head))
uv run alembic history                                         # list all migrations, oldest → newest
uv run alembic heads                                           # show the latest revision in each branch
uv run alembic show <revision>                                 # print details of a specific migration
```
