import textwrap
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from async_db import get_async_db_session
from models import PostModel, UserModel
from schemas import (
    PostResponseSchema,
    UserPublicSchema,
)

templates = Jinja2Templates(directory="templates")
router = APIRouter()


@router.get("/", include_in_schema=False, name="home")
@router.get("/posts", include_in_schema=False, name="posts")
async def home(
    request: Request, session: Annotated[AsyncSession, Depends(get_async_db_session)]
):
    result = await session.execute(
        select(PostModel)
        .options(selectinload(PostModel.author))
        .order_by(PostModel.date_posted.desc())
    )
    posts = result.scalars().all()

    return templates.TemplateResponse(
        request,
        "home.html",
        {
            "posts": [PostResponseSchema.model_validate(post) for post in posts],
            "title": "Home",
        },
    )


@router.get("/posts/{post_id}", include_in_schema=False, name="post_page")
async def post_page(
    request: Request,
    post_id: int,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
):
    result = await session.execute(
        select(PostModel)
        .options(selectinload(PostModel.author))
        .where(PostModel.id == post_id)
    )
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


@router.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts_page")
async def user_posts_page(
    request: Request,
    user_id: int,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
):
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    result = await session.execute(
        select(PostModel)
        .options(selectinload(PostModel.author))
        .where(PostModel.user_id == user_id)
        .order_by(PostModel.date_posted.desc())
    )
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


@router.get("/login", include_in_schema=False)
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"title": "Login"})


@router.get("/register", include_in_schema=False)
async def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {"title": "Register"})


@router.get("/account", include_in_schema=False)
async def account_page(request: Request):
    return templates.TemplateResponse(request, "account.html", {"title": "Account"})
