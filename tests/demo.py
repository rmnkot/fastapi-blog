# File should be named test_demo.py to be recognized
from fastapi import FastAPI
from fastapi.testclient import TestClient

demo_app = FastAPI()


@demo_app.get("/")
def demo_home():
    return {"message": "Hello"}


client = TestClient(demo_app)


# Setup for synchronous testing approach


def test_homepage():
    response = client.get("/")
    assert response.status_code == 200
