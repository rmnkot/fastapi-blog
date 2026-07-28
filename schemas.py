from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)


class UserCreate(UserBase):
    pass


class UserUpdate(BaseModel):
    username: str | None = Field(min_length=1, max_length=50, default=None)
    email: EmailStr | None = Field(max_length=120, default=None)
    image_file: str | None = Field(min_length=1, max_length=200, default=None)


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_file: str | None
    image_path: str


class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    user_id: int  # Temporary


class PostUpdate(BaseModel):
    title: str | None = Field(min_length=1, max_length=50, default=None)
    content: str | None = Field(min_length=1, default=None)


class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date_posted: datetime
    author: UserResponse
