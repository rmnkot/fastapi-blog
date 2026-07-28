from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from async_db import get_async_db_session
from schemas import (
    PostCreate,
    PostResponse,
    PostUpdate,
)

router = APIRouter()


@router.get("")
async def get_posts(
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> list[PostResponse]:
    result = await session.execute(select(models.Post))
    posts = result.scalars().all()

    return [PostResponse.model_validate(post) for post in posts]


@router.get("/{post_id}")
async def get_post(
    post_id: int, session: Annotated[AsyncSession, Depends(get_async_db_session)]
) -> PostResponse:
    result = await session.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    return PostResponse.model_validate(post)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreate, session: Annotated[AsyncSession, Depends(get_async_db_session)]
) -> PostResponse:
    result = await session.execute(
        select(models.User).where(models.User.id == payload.user_id)
    )
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    new_post = models.Post(
        title=payload.title, content=payload.content, user_id=payload.user_id
    )

    session.add(new_post)
    await session.commit()
    await session.refresh(new_post, attribute_names=["author"])

    return PostResponse.model_validate(new_post)


@router.put("/{post_id}")
async def update_post_full(
    post_id: int,
    post_data: PostCreate,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> PostResponse:
    result = await session.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    if post_data.user_id != post.user_id:
        result = await session.execute(
            select(models.User).where(models.User.id == post_data.user_id)
        )
        user = result.scalars().first()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
            )

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    await session.commit()
    await session.refresh(post, attribute_names=["author"])

    return PostResponse.model_validate(post)


@router.patch("/{post_id}")
async def update_post_partial(
    post_id: int,
    post_data: PostUpdate,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> PostResponse:
    result = await session.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await session.commit()
    await session.refresh(post, attribute_names=["author"])

    return PostResponse.model_validate(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int, session: Annotated[AsyncSession, Depends(get_async_db_session)]
):
    result = await session.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.id == post_id)
    )
    post = result.scalars().first()
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    await session.delete(post)
    await session.commit()
