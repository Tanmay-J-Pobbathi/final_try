import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from main import app, get_db
from database import Base
from config import settings

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


Base.metadata.create_all(bind=engine)


def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_and_teardown():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


def test_create_user():
    response = client.post(
        "/users/",
        json={"username": "testuser", "password": "testpassword"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data
    assert "todos" in data


def get_token():
    client.post(
        "/users/",
        json={"username": "testuser", "password": "testpassword"},
    )
    response = client.post(
        "/token",
        data={"username": "testuser", "password": "testpassword"},
    )
    return response.json()["access_token"]


def test_login_for_access_token():
    token = get_token()
    assert token is not None


def test_read_todos_unauthorized():
    response = client.get("/todos/")
    assert response.status_code == 401


def test_create_and_read_todo():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/todos/",
        headers=headers,
        json={"title": "Test Todo", "description": "Test Description"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Test Todo"
    assert data["description"] == "Test Description"
    todo_id = data["id"]

    response = client.get(f"/todos/{todo_id}", headers=headers)
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Test Todo"


def test_update_todo():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/todos/",
        headers=headers,
        json={"title": "Test Todo", "description": "Test Description"},
    )
    todo_id = response.json()["id"]

    response = client.put(
        f"/todos/{todo_id}",
        headers=headers,
        json={"title": "Updated Todo", "description": "Updated Description"},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["title"] == "Updated Todo"


def test_patch_todo():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/todos/",
        headers=headers,
        json={"title": "Test Todo", "description": "Test Description"},
    )
    todo_id = response.json()["id"]

    response = client.patch(
        f"/todos/{todo_id}",
        headers=headers,
        json={"completed": True},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["completed"] is True


def test_delete_todo():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}"}
    response = client.post(
        "/todos/",
        headers=headers,
        json={"title": "Test Todo", "description": "Test Description"},
    )
    todo_id = response.json()["id"]

    response = client.delete(f"/todos/{todo_id}", headers=headers)
    assert response.status_code == 200, response.text

    response = client.get(f"/todos/{todo_id}", headers=headers)
    assert response.status_code == 404
