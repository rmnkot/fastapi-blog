from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from async_db import Session
from auth import CurrentUserModel
from config import settings
from models import PostModel
from schemas import (
    PaginatedPostResponseSchema,
    PostCreateSchema,
    PostResponseSchema,
    PostUpdateSchema,
)

router = APIRouter()


@router.get("")
async def get_posts(
    session: Session,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.post_per_page,
) -> PaginatedPostResponseSchema:
    count_result = await session.execute(select(func.count()).select_from(PostModel))
    total = count_result.scalar() or 0

    result = await session.execute(
        select(PostModel)
        .options(selectinload(PostModel.author))
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


@router.get("/{post_id}")
async def get_post(
    post_id: int,
    session: Session,
) -> PostResponseSchema:
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

    return PostResponseSchema.model_validate(post)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_post(
    payload: PostCreateSchema,
    current_user: CurrentUserModel,
    session: Session,
) -> PostResponseSchema:
    new_post = PostModel(
        title=payload.title,
        content=payload.content,
        user_id=current_user.id,
    )

    session.add(new_post)
    await session.commit()
    await session.refresh(new_post, attribute_names=["author"])

    return PostResponseSchema.model_validate(new_post)


@router.put("/{post_id}")
async def update_post_full(
    post_id: int,
    post_data: PostCreateSchema,
    current_user: CurrentUserModel,
    session: Session,
) -> PostResponseSchema:
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

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    post.title = post_data.title
    post.content = post_data.content

    await session.commit()
    await session.refresh(post, attribute_names=["author"])

    return PostResponseSchema.model_validate(post)


@router.patch("/{post_id}")
async def update_post_partial(
    post_id: int,
    post_data: PostUpdateSchema,
    current_user: CurrentUserModel,
    session: Session,
) -> PostResponseSchema:
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

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this post",
        )

    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    await session.commit()
    await session.refresh(post, attribute_names=["author"])

    return PostResponseSchema.model_validate(post)


@router.delete("/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(
    post_id: int,
    current_user: CurrentUserModel,
    session: Session,
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

    if post.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this post",
        )

    await session.delete(post)
    await session.commit()
