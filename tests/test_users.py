from io import BytesIO
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from config import settings
from tests.conftest import authorize_user, create_test_user


@pytest.mark.anyio
async def test_create_user_validation_error(client: AsyncClient):
    response = await client.post("/api/users", json={"username": "testuser"})

    assert response.status_code == 422
    assert "email" in response.text
    assert "password" in response.text


@pytest.mark.anyio
async def test_create_user_duplicate_email(client: AsyncClient):
    await create_test_user(client)

    response = await client.post(
        "/api/users",
        json={
            "username": "different_user",
            "email": "test@example.com",
            "password": "password123",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Email already exists"


@pytest.mark.anyio
async def test_create_user_success(client: AsyncClient):
    data = await create_test_user(
        client, username="new_user", email="new@example.com", password="12345678"
    )

    assert data["username"] == "new_user"
    assert data["email"] == "new@example.com"
    assert "id" in data
    assert "image_path" in data
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_upload_profile_picture(client: AsyncClient, mocked_aws):
    user, headers = await authorize_user(client)

    test_image_path = Path(__file__).parent / "test_image.jpg"
    image_bytes = test_image_path.read_bytes()
    response = await client.patch(
        f"/api/users/{user['id']}/picture",
        files={"file": ("profile.jpg", BytesIO(image_bytes), "image/jpg")},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["image_file"] is not None
    assert data["image_file"].endswith(".jpg")
    assert "s3" in data["image_path"]

    s3_object = mocked_aws.list_objects_v2(Bucket=settings.s3_bucket_name)
    assert "Contents" in s3_object
    assert len(s3_object["Contents"]) == 1
    assert s3_object["Contents"][0]["Key"].endswith(data["image_file"])


@pytest.mark.anyio
async def test_forgot_password_sends_email(client: AsyncClient):
    await create_test_user(
        client, username="new_user", email="new@example.com", password="12345678"
    )

    with patch(
        "routers.users.send_password_reset_email", new_callable=AsyncMock
    ) as mock_send:
        response = await client.post(
            "/api/users/forgot-password",
            json={"email": "new@example.com"},
        )

        assert response.status_code == 202
        mock_send.assert_awaited_once()
        call_kwargs = mock_send.call_args.kwargs
        assert call_kwargs["to_email"] == "new@example.com"
        assert call_kwargs["username"] == "new_user"
        assert "token" in call_kwargs
