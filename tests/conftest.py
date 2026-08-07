import os

# Redeclaring environment variables for configuration
os.environ["POSTGRES_USER"] = "blog_user"
os.environ["POSTGRES_PASSWORD"] = "password"
os.environ["POSTGRES_PORT"] = "5432"
os.environ["TEST_POSTGRES_DB"] = "test_blog_db"  # drives settings.test_database_url
os.environ["S3_BUCKET_NAME"] = "test-bucket"
os.environ["SECRET_KEY"] = (
    "17544690a88bfe6b32b00b8487c914e80dc50f445a933059628158efb792d75f"
)

os.environ["S3_ACCESS_KEY_ID"] = "testing"
os.environ["S3_SECRET_ACCESS_KEY"] = "testing"
os.environ["S3_REGION"] = "eu-north-1"

# env variables overrides for boto3
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "eu-north-1"

from collections.abc import AsyncGenerator
from typing import cast

import boto3
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from mypy_boto3_s3.literals import BucketLocationConstraintType
from sqlalchemy import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from async_db import Base, get_async_db_session
from config import settings
from main import app

pytest_plugins = ["anyio"]


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
    return engine


@pytest.fixture(scope="session")
async def setup_database(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def db_session(
    test_engine,
    setup_database,
) -> AsyncGenerator[AsyncSession]:
    conn = await test_engine.connect()
    transaction = await conn.begin()

    test_async_session = async_sessionmaker(
        bind=conn,
        class_=AsyncSession,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )

    async with test_async_session() as session:
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()
            await conn.close()


@pytest.fixture
def mocked_aws():
    with mock_aws():
        s3 = boto3.client("s3", region_name=settings.s3_region)
        s3.create_bucket(
            Bucket=settings.s3_bucket_name,
            # Required by moto/AWS for any region other than us-east-1.
            CreateBucketConfiguration={
                "LocationConstraint": cast(
                    BucketLocationConstraintType, settings.s3_region
                ),
            },
        )
        yield s3


@pytest.fixture
async def client(
    db_session: AsyncSession,
    mocked_aws,
) -> AsyncGenerator[AsyncClient]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_async_db_session] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    app.dependency_overrides.clear()


async def create_test_user(
    client: AsyncClient,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> dict:
    response = await client.post(
        "/api/users",
        json={"username": username, "email": email, "password": password},
    )
    assert response.status_code == 201, f"Failed to create user: {response.text}"
    return response.json()


async def login_user(
    client: AsyncClient,
    email: str = "test@example.com",
    password: str = "testpassword123",
) -> str:
    response = await client.post(
        "/api/users/token",
        # data - form data
        data={"username": email, "password": password},
    )
    assert response.status_code == 200, f"Failed to login: {response.text}"
    return response.json()["access_token"]


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def authorize_user(
    client: AsyncClient,
    username: str = "testuser",
    email: str = "test@example.com",
    password: str = "testpassword123",
):
    user = await create_test_user(
        client,
        username,
        email,
        password,
    )
    token = await login_user(client, email, password)
    headers = auth_header(token)

    return user, headers
