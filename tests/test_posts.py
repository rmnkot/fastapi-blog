import pytest
from httpx import AsyncClient

from tests.conftest import authorize_user


@pytest.mark.anyio
async def test_get_posts_empty(client: AsyncClient):
    response = await client.get("/api/posts")

    assert response.status_code == 200
    data = response.json()
    assert data["posts"] == []
    assert data["total"] == 0
    assert data["has_more"] is False


@pytest.mark.anyio
async def test_get_post_not_found(client: AsyncClient):
    response = await client.get("/api/posts/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"


@pytest.mark.anyio
async def test_create_post_success(client: AsyncClient):
    # user = await create_test_user(client)
    # token = await login_user(client)
    # headers = auth_header(token)
    user, headers = await authorize_user(client)
    response = await client.post(
        "/api/posts",
        json={"title": "My first post", "content": "This is the content"},
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My first post"
    assert data["content"] == "This is the content"
    assert data["user_id"] == user["id"]
    assert "id" in data
    assert "date_posted" in data
    assert data["author"]["username"] == "testuser"


@pytest.mark.anyio
async def test_create_post_unauthorized(client: AsyncClient):
    response = await client.post(
        "/api/posts",
        json={"title": "My first post", "content": "This is the content"},
    )

    assert response.status_code == 401
    data = response.json()
    assert data["detail"] == "Not authenticated"


@pytest.mark.anyio
async def test_update_post_success(client: AsyncClient):
    _user, headers = await authorize_user(client)
    response = await client.post(
        "/api/posts",
        json={"title": "Original title", "content": "Original content"},
        headers=headers,
    )
    post_id = response.json()["id"]

    response = await client.patch(
        f"/api/posts/{post_id}",
        json={"title": "Updated title"},
        headers=headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated title"
    assert data["content"] == "Original content"


@pytest.mark.anyio
async def test_update_post_wrong_user(client: AsyncClient):
    _user1, headers1 = await authorize_user(
        client, username="user1", email="user1@example.com"
    )
    response = await client.post(
        "/api/posts",
        json={"title": "User 1's Post", "content": "Only user 1 can edit this"},
        headers=headers1,
    )
    post_id = response.json()["id"]

    _user2, headers2 = await authorize_user(
        client, username="user2", email="user2@example.com"
    )
    response = await client.patch(
        f"/api/posts/{post_id}",
        json={"title": "Hacked title"},
        headers=headers2,
    )

    assert response.status_code == 403
    data = response.json()
    assert data["detail"] == "Not authorized to update this post"


@pytest.mark.anyio
async def test_get_posts_with_pagination(client: AsyncClient):
    _user, headers = await authorize_user(client)

    for i in range(5):
        response = await client.post(
            "/api/posts",
            json={"title": f"Post {i}", "content": f"Content for post {i}"},
            headers=headers,
        )
        assert response.status_code == 201

    response = await client.get("/api/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["posts"]) == 5
    assert data["has_more"] is False

    response = await client.get("/api/posts?limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["posts"]) == 2
    assert data["has_more"] is True

    response = await client.get("/api/posts?skip=2&limit=3")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["posts"]) == 3
    assert data["skip"] == 2
    assert data["limit"] == 3
    assert data["has_more"] is False
