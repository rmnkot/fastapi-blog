from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from PIL import UnidentifiedImageError
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.concurrency import run_in_threadpool

from async_db import Session
from auth import (
    CurrentUserModel,
    create_access_token,
    generate_reset_token,
    hash_password,
    hash_reset_token,
    verify_password,
)
from config import settings
from email_utils import send_password_reset_email
from image_utils import delete_profile_image, process_profile_image
from models import PasswordResetTokenModel, PostModel, UserModel
from schemas import (
    ChangePasswordRequestSchema,
    ForgotPasswordRequestSchema,
    PaginatedPostResponseSchema,
    PostResponseSchema,
    ResetPasswordRequestSchema,
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
    session: Session,
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
    current_user: CurrentUserModel,
) -> UserPrivateSchema:
    return UserPrivateSchema.model_validate(current_user)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequestSchema,
    background_tasks: BackgroundTasks,
    session: Session,
) -> dict[str, str]:
    result = await session.execute(
        select(UserModel).where(
            func.lower(UserModel.email) == request_data.email.lower()
        )
    )
    user = result.scalars().first()
    if user:
        # Delete any existing token for reset password
        await session.execute(
            sql_delete(PasswordResetTokenModel).where(
                PasswordResetTokenModel.user_id == user.id
            )
        )

        token = generate_reset_token()
        token_hash = hash_reset_token(token)
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.reset_token_expire_minutes
        )

        reset_token = PasswordResetTokenModel(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at
        )
        session.add(reset_token)
        await session.commit()

        background_tasks.add_task(
            send_password_reset_email,
            to_email=user.email,
            username=user.username,
            token=token,
        )

    #  This generic message with 202 response prevents email enumeration attack, we are not exposing info whether email exists or not
    return {
        "message": "If an account exists with this email, you will receive password reset instructions."
    }


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    request_data: ResetPasswordRequestSchema, session: Session
) -> dict[str, str]:
    token_hash = hash_reset_token(request_data.token)

    result = await session.execute(
        select(PasswordResetTokenModel).where(
            PasswordResetTokenModel.token_hash == token_hash
        )
    )
    reset_token = result.scalars().first()
    if not reset_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",  # Hide actual info behind generic message
        )

    # replace(tzinfo=UTC) is a workaround for SQLite to bring back timezone info to date string,
    # not needed for PostgreSQL
    if reset_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        await session.delete(reset_token)
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",  # Hide actual info behind generic message
        )

    result = await session.execute(
        select(UserModel).where(UserModel.id == reset_token.user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",  # Hide actual info behind generic message
        )

    user.password_hash = hash_password(request_data.new_password)

    await session.execute(
        sql_delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == user.id
        )
    )
    await session.commit()

    # No automatic user login for security best practices and simplification
    return {
        "message": "Password reset successfully. You can now log in with your new password."
    }


@router.patch("/me/password", status_code=status.HTTP_200_OK)
async def change_password(
    request_data: ChangePasswordRequestSchema,
    current_user: CurrentUserModel,
    session: Session,
) -> dict[str, str]:
    if not verify_password(request_data.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = hash_password(request_data.new_password)

    await session.execute(
        sql_delete(PasswordResetTokenModel).where(
            PasswordResetTokenModel.user_id == current_user.id
        )
    )
    await session.commit()

    return {"message": "Password changed successfully"}


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    session: Session,
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
    session: Session,
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
    current_user: CurrentUserModel,
    session: Session,
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

    if (
        user_data.username is not None
        and user_data.username.lower() != user.username.lower()
    ):
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

    if user_data.email is not None and user_data.email.lower() != user.email.lower():
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

    await session.commit()
    await session.refresh(user)

    return UserPrivateSchema.model_validate(user)


@router.get("/{user_id}/posts")
async def get_user_posts(
    user_id: int,
    session: Session,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.post_per_page,
) -> PaginatedPostResponseSchema:
    result = await session.execute(select(UserModel).where(UserModel.id == user_id))
    user = result.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )

    count_result = await session.execute(
        select(func.count()).select_from(PostModel).where(PostModel.user_id == user_id)
    )
    total = count_result.scalar() or 0

    result = await session.execute(
        select(PostModel)
        .options(selectinload(PostModel.author))
        .where(PostModel.user_id == user_id)
        .order_by(PostModel.date_posted.desc())
        .offset(skip)
        .limit(limit)
    )
    posts = result.scalars().all()
    has_more = skip + len(posts) < total

    return PaginatedPostResponseSchema(
        posts=[PostResponseSchema.model_validate(post) for post in posts],
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: CurrentUserModel,
    session: Session,
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

    old_filename = user.image_file

    await session.delete(user)
    await session.commit()

    if old_filename:
        delete_profile_image(old_filename)


@router.patch("/{user_id}/picture")
async def upload_profile_picture(
    user_id: int,
    file: UploadFile,
    current_user: CurrentUserModel,
    session: Session,
) -> UserPrivateSchema:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user picture",
        )

    content = await file.read()
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size is {settings.max_upload_size_bytes // 1024 * 1024}MB",
        )

    try:
        new_filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image file. Please upload valid image (JPEG, PNG, GIF, WebP).",
        ) from error

    old_filename = current_user.image_file
    current_user.image_file = new_filename
    await session.commit()
    await session.refresh(current_user)

    if old_filename:
        delete_profile_image(old_filename)

    return UserPrivateSchema.model_validate(current_user)


@router.delete("/{user_id}/picture")
async def delete_user_picture(
    user_id: int,
    current_user: CurrentUserModel,
    session: Session,
) -> UserPrivateSchema:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this user picture",
        )

    old_filename = current_user.image_file
    if old_filename is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No profile picture to delete.",
        )

    current_user.image_file = None
    await session.commit()
    await session.refresh(current_user)

    delete_profile_image(old_filename)
    return UserPrivateSchema.model_validate(current_user)
