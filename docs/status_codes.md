## Status codes

* **200 OK** - Successful GET, PUT, or PATCH
* **201 Created** - Successful POST for users and posts
* **202 Accepted** - `POST /forgot-password` (reset email accepted for delivery)
* **204 No Content** - Successful DELETE
* **400 Bad Request** - Duplicate username/email when creating user
* **401 Unauthorized** - Missing or invalid credentials (login/token)
* **403 Forbidden** - Authenticated user not authorized to access or modify a resource (e.g. another user's posts or account)
* **404 Not Found** - Resource doesn't exist (user or post)
* **422 Unprocessable Entity** - Validation error (automatic from Pydantic)