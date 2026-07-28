## Status codes

* **200 OK** - Successful GET, PUT, or PATCH
* **201 Created** - Successful POST for users and posts
* **204 No Content** - Successful DELETE
* **400 Bad Request** - Duplicate username/email when creating user
* **404 Not Found** - Resource doesn't exist (user or post)
* **422 Unprocessable Entity** - Validation error (automatic from Pydantic)*