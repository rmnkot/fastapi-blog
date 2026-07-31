---
description: "Use when writing, editing, or refactoring FastAPI API routers in routers/ (users.py, posts.py). Covers route patterns, status codes, response schemas, and error handling."
applyTo: "routers/**/*.py"
---
# API Router Guidelines

- Define handlers as `async def` with the annotated session dependency:
  ```python
  async def get_posts(
      session: Annotated[AsyncSession, Depends(get_async_db_session)],
  ) -> list[PostResponseSchema]:
  ```
- Protect authenticated routes with `current_user: CurrentUser`; guard ownership inside the handler (`post.user_id != current_user.id` → 403).
- Return Pydantic response schemas with `Schema.model_validate(obj)` — never raw ORM objects, and always annotate the return type.
- Eager-load relationships before serializing: `select(PostModel).options(selectinload(PostModel.author))`.
- Status codes per method:
  - `GET`, `PUT`, `PATCH` → default `200`
  - `POST` → `status_code=status.HTTP_201_CREATED` on the decorator
  - `DELETE` → `status_code=status.HTTP_204_NO_CONTENT` on the decorator
  - missing resource → `404` with a short `detail`
  - wrong owner → `403`
  - auth failure → `401` with `headers={"WWW-Authenticate": "Bearer"}`
- After writes: `await session.commit()`, then `await session.refresh(obj, attribute_names=["author"])` to reload lazy relationships.
- Full replace uses `PUT` with the `*Create` schema; partial update uses `PATCH` applying `model_dump(exclude_unset=True)`.
- Case-insensitive uniqueness checks: `where(func.lower(Model.col) == value.lower())`.
- Order routes so static paths (`/me`, `/token`) are declared before parameterized ones (`/{user_id}`).
