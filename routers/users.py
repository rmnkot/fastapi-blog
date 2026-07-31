from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from async_db import get_async_db_session
from auth import (
    CurrentUser,
    create_access_token,
    hash_password,
    verify_password,
)
from config import settings
from models import PostModel, UserModel
from schemas import (
    PostResponseSchema,
    TokenSchema,
    UserCreateSchema,
    UserPrivateSchema,
    UserPublicSchema,
    UserUpdateSchema,
)

router = APIRouter()


@router.post("/token")
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> TokenSchema:
    # Lookup user by email (case-insensitive)
    # Note: OAuth2PasswordRequestForm uses "username" field, but we treat it as email
    result = await session.execute(
        select(UserModel).where(
            func.lower(UserModel.email) == form_data.username.lower()
        )
    )
    user = result.scalars().first()

    # Verify user exists and password is correct
    # Never reveal which one failed (security best practice)
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create access token with user id and subject
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )

    return TokenSchema(access_token=access_token, token_type="bearer")


@router.get("/me")
async def get_current_user(
    current_user: CurrentUser,
) -> UserPrivateSchema:
    return UserPrivateSchema.model_validate(current_user)


@router.get("/{user_id}")
async def get_user(
    user_id: int, session: Annotated[AsyncSession, Depends(get_async_db_session)]
) -> UserPublicSchema:
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    existing_user = result.scalars().first()

    if not existing_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return UserPublicSchema.model_validate(existing_user)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreateSchema,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> UserPrivateSchema:
    result = await session.execute(
        select(UserModel).where(
            func.lower(UserModel.username) == payload.username.lower()
        )
    )
    existing_user = result.scalars().first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User already exists"
        )

    result = await session.execute(
        select(UserModel).where(func.lower(UserModel.email) == payload.email.lower())
    )
    existing_email = result.scalars().first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists"
        )

    new_user = UserModel(
        username=payload.username,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
    )
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return UserPrivateSchema.model_validate(new_user)


@router.patch("/{user_id}")
async def update_user(
    user_id: int,
    user_data: UserUpdateSchema,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
) -> UserPrivateSchema:
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user",
        )

    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    if user_data.username is not None and user_data.username != user.username:
        result = await session.execute(
            select(UserModel).where(
                func.lower(UserModel.username) == user_data.username.lower()
            )
        )
        existing_username = result.scalars().first()
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already exists.",
            )

    if user_data.email is not None and user_data.email != user.email:
        result = await session.execute(
            select(UserModel).where(
                func.lower(UserModel.email) == user_data.email.lower()
            )
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
        user.email = user_data.email.lower()
    if user_data.image_file is not None:
        user.image_file = user_data.image_file

    await session.commit()
    await session.refresh(user)

    return UserPrivateSchema.model_validate(user)


@router.get("/{user_id}/posts")
async def get_user_posts(
    user_id: int, session: Annotated[AsyncSession, Depends(get_async_db_session)]
) -> list[PostResponseSchema]:
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    result = await session.execute(
        select(PostModel)
        .options(selectinload(PostModel.author))
        .where(PostModel.user_id == user_id)
        .order_by(PostModel.date_posted.desc())
    )
    posts = result.scalars().all()

    return [PostResponseSchema.model_validate(post) for post in posts]


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_async_db_session)],
):
    if user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this user",
        )

    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    await session.delete(user)
    await session.commit()
