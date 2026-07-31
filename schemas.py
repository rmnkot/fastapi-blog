from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBaseSchema(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    email: EmailStr = Field(max_length=120)


class UserCreateSchema(UserBaseSchema):
    password: str = Field(min_length=8)


class UserUpdateSchema(BaseModel):
    username: str | None = Field(min_length=1, max_length=50, default=None)
    email: EmailStr | None = Field(max_length=120, default=None)
    image_file: str | None = Field(min_length=1, max_length=200, default=None)


class UserPublicSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    image_file: str | None
    image_path: str


class UserPrivateSchema(UserPublicSchema):
    email: EmailStr


class TokenSchema(BaseModel):
    access_token: str
    token_type: str


class PostBaseSchema(BaseModel):
    title: str = Field(min_length=1, max_length=50)
    content: str = Field(min_length=1)


class PostCreateSchema(PostBaseSchema):
    pass


class PostUpdateSchema(BaseModel):
    title: str | None = Field(min_length=1, max_length=50, default=None)
    content: str | None = Field(min_length=1, default=None)


class PostResponseSchema(PostBaseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    date_posted: datetime
    author: UserPublicSchema
