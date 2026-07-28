from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

import models
from async_db import get_async_db_session
from schemas import (
    PostResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)

router = APIRouter()


@router.get("/{user_id}")
async def get_user(
    user_id: int, session: Annotated[AsyncSession, Depends(get_async_db_session)]
) -> UserResponse:
    result = await session.execute(select(models.User).where(models.User.id == user_id))
    existing_user = result.scalars().first()

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserResponse.model_validate(existing_user)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate, session: Annotated[AsyncSession, Depends(get_async_db_session)]
) -> UserResponse:
    result = await session.execute(
        select(models.User).where(models.User.username == payload.username)
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )

    result = await session.execute(
        select(models.User).where(models.User.email == payload.email)
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    new_user = models.User(username=payload.username, email=payload.email)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return UserResponse.model_validate(new_user)


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> UserResponse:
    result = await session.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_data.username is not None and user_data.username != user.username:
        result = await session.execute(
            select(models.User).where(models.User.username == user_data.username)
        )
        existing_username = result.scalars().first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists.",
            )

    if user_data.email is not None and user_data.email != user.email:
        result = await session.execute(
            select(models.User).where(models.User.email == user_data.email)
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

    await session.commit()
    await session.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/{user_id}/posts")
async def get_user_posts(
    user_id: int, session: Annotated[AsyncSession, Depends(get_async_db_session)]
) -> list[PostResponse]:
    result = await session.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    result = await session.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .where(models.Post.user_id == user_id)
    )
    posts = result.scalars().all()

    return [PostResponse.model_validate(post) for post in posts]


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int, session: Annotated[AsyncSession, Depends(get_async_db_session)]
):
    result = await session.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await session.delete(user)
    await session.commit()
