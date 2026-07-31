import textwrap
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from models import PostModel, UserModel
from schemas import (
    PostCreateSchema,
    PostResponseSchema,
    PostUpdateSchema,
    UserCreateSchema,
    UserPrivateSchema,
    UserPublicSchema,
    UserUpdateSchema,
)
from sync_db import Base, engine, get_db_session

Base.metadata.create_all(bind=engine)

app = FastAPI(version="v1")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/media", StaticFiles(directory="media"), name="media")

templates = Jinja2Templates(directory="templates")


# ================= TEMPLATE ROUTS ===================


@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
def home(request: Request, session: Annotated[Session, Depends(get_db_session)]):
    result = session.execute(select(PostModel))
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": [PostResponseSchema.model_validate(post) for post in posts],
            "title": "Home",
        },
    )


@app.get("/posts/{post_id}", include_in_schema=False, name="post_page")
def post_page(
    request: Request, post_id: int, session: Annotated[Session, Depends(get_db_session)]
):
    result = session.execute(select(PostModel).where(PostModel.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return templates.TemplateResponse(
        request,
        "post.html",
        {
            "post": PostResponseSchema.model_validate(post),
            "title": textwrap.shorten(post.title, width=12, placeholder="..."),
        },
    )


@app.get("/users/{user_id}/posts", name="user_posts_page")
def user_posts_page(
    request: Request, user_id: int, session: Annotated[Session, Depends(get_db_session)]
):
    result = session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    result = session.execute(select(PostModel).where(PostModel.user_id == user_id))
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "user_posts.html",
        {
            "user": UserPublicSchema.model_validate(user),
            "posts": [PostResponseSchema.model_validate(post) for post in posts],
            "title": f"{user.username}'s posts",
        },
    )


# ================= API ROUTS ===================


@app.get("/api/users/{user_id}")
def get_user(
    user_id: int, session: Annotated[Session, Depends(get_db_session)]
) -> UserPublicSchema:
    result = session.execute(select(UserModel).where(UserModel.id == user_id))
    existing_user = result.scalars().first()

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserPublicSchema.model_validate(existing_user)


@app.post("/api/users", status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateSchema, session: Annotated[Session, Depends(get_db_session)]
) -> UserPrivateSchema:
    result = session.execute(
        select(UserModel).where(UserModel.username == payload.username)
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )

    result = session.execute(select(UserModel).where(UserModel.email == payload.email))
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    new_user = UserModel(username=payload.username, email=payload.email)
    session.add(new_user)
    session.commit()
    session.refresh(new_user)

    return UserPrivateSchema.model_validate(new_user)


@app.patch("/api/users/{user_id}")
def update_user(
    user_id: int,
    user_data: UserUpdateSchema,
    session: Annotated[Session, Depends(get_db_session)],
) -> UserPrivateSchema:
    result = session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_data.username is not None and user_data.username != user.username:
        result = session.execute(
            select(UserModel).where(UserModel.username == user_data.username)
        )
        existing_username = result.scalars().first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists.",
            )

    if user_data.email is not None and user_data.email != user.email:
        result = session.execute(
            select(UserModel).where(UserModel.email == user_data.email)
        )
        existing_email = result.scalars().first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists."
            )

    # updated_data = user_data.model_dump(exclude_unset=True)
    # for field, value in updated_data.items():
    #     setattr(user, field, value)

    # Alternative for user_data.model_dump approach
    if user_data.username is not None:
        user.username = user_data.username
    if user_data.email is not None:
        user.email = user_data.email
    if user_data.image_file is not None:
        user.image_file = user_data.image_file

    session.commit()
    session.refresh(user)

    return UserPrivateSchema.model_validate(user)


@app.get("/api/users/{user_id}/posts")
def get_user_posts(
    user_id: int, session: Annotated[Session, Depends(get_db_session)]
) -> list[PostResponseSchema]:
    result = session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    result = session.execute(select(PostModel).where(PostModel.user_id == user_id))
    posts = result.scalars().all()

    return [PostResponseSchema.model_validate(post) for post in posts]


@app.delete("/api/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(user_id: int, session: Annotated[Session, Depends(get_db_session)]):
    result = session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    session.delete(user)
    session.commit()


@app.get("/api/posts")
def get_posts(
    session: Annotated[Session, Depends(get_db_session)],
) -> list[PostResponseSchema]:
    result = session.execute(select(PostModel))
    posts = result.scalars().all()

    return [PostResponseSchema.model_validate(post) for post in posts]


@app.get("/api/posts/{post_id}")
def get_post(
    post_id: int, session: Annotated[Session, Depends(get_db_session)]
) -> PostResponseSchema:
    result = session.execute(select(PostModel).where(PostModel.id == post_id))
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return PostResponseSchema.model_validate(post)


@app.post("/api/posts/", status_code=status.HTTP_201_CREATED)
def create_post(
    payload: PostCreateSchema, session: Annotated[Session, Depends(get_db_session)]
) -> PostResponseSchema:
    result = session.execute(select(UserModel).where(UserModel.id == payload.user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    new_post = PostModel(
        title=payload.title, content=payload.content, user_id=payload.user_id
    )

    session.add(new_post)
    session.commit()
    session.refresh(new_post)

    return PostResponseSchema.model_validate(new_post)


@app.put("/api/posts/{post_id}")
def update_post_full(
    post_id: int,
    post_data: PostCreateSchema,
    session: Annotated[Session, Depends(get_db_session)],
) -> PostResponseSchema:
    result = session.execute(select(PostModel).where(PostModel.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    if not post_data.user_id != post.user_id:
        result = session.execute(
            select(UserModel).where(UserModel.id == post_data.user_id)
        )
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    session.commit()
    session.refresh(post)

    return PostResponseSchema.model_validate(post)


@app.patch("/api/posts/{post_id}")
def update_post_partial(
    post_id: int,
    post_data: PostUpdateSchema,
    session: Annotated[Session, Depends(get_db_session)],
) -> PostResponseSchema:
    result = session.execute(select(PostModel).where(PostModel.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    session.commit()
    session.refresh(post)

    return PostResponseSchema.model_validate(post)


@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, session: Annotated[Session, Depends(get_db_session)]):
    result = session.execute(select(PostModel).where(PostModel.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    session.delete(post)
    session.commit()


# ================= ERROR HANDLING ===================


@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=exception.status_code, content={"detail": message}
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )

    return templates.TemplateResponse(
        request,
        "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
