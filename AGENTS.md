# FastAPI Blog — Project Guidelines

## Code Style

- Python 3.14+ with modern typing: use `X | None` instead of `Optional[X]`.
- SQLAlchemy 2.0 style: `Mapped[...]` + `mapped_column(...)` on declarative models (see `models.py`).
- Pydantic v2 schemas: response schemas set `model_config = ConfigDict(from_attributes=True)`; name schemas with `Base` / `Create` / `Update` / `Response` suffixes (see `schemas.py`).
- Always use `Annotated[...]` for dependencies, e.g. `session: Annotated[AsyncSession, Depends(get_async_db_session)]`.
- Always return response schemas, never ORM objects directly: `Schema.model_validate(obj)`.
- Formatting/linting: Ruff (preview formatting) and Pyright (`typeCheckingMode = "standard"`) are configured in `pyproject.toml`.

## Architecture

- **Async-only**: the app lives in `main.py` (entrypoint `main:app`). `main_sync.py` and `sync_db.py` are deprecated — do not modify them; keep all new code async.
- `async_db.py` owns the async engine, `AsyncSessionLocal`, and `Base`. Models import `Base` from `async_db`.
- Routers in `routers/`:
  - `templates.py` → HTML pages (Jinja2, mounted without a prefix)
  - `users.py` → `/api/users`
  - `posts.py` → `/api/posts`
- Auth lives in `auth.py` (JWT + argon2). Protect endpoints with the `CurrentUser` dependency.
- Error handling: `HTTPException` with `status.HTTP_4XX` constants; API paths return JSON, page paths render `error.html` (see handlers in `main.py`).

## Build and Test

- Package manager: `uv` (see `uv.lock`).
- Dev server: `uv run fastapi dev` (entrypoint `main:app`).
- Lint / type check: `uv run ruff check .` and `uv run pyright`.

## Conventions

- Eager-load relationships with `selectinload(...)` (e.g. `PostModel.author`) before serializing.
- Case-insensitive uniqueness lookups use `func.lower(...)` (see `routers/users.py`).
- 401 responses include `headers={"WWW-Authenticate": "Bearer"}`; unauthorized access to a resource → 403; missing resource → 404 with a short `detail`.
- Templates render with `templates.TemplateResponse(request, "x.html", {...})`.
- See `docs/sataus_codes.md` for the HTTP status code conventions used across the API.
