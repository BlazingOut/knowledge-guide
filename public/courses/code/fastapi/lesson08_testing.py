import sqlite3
from pathlib import Path
from typing import Generator

import pytest
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel


DATABASE = Path(__file__).parent / "study.sqlite3"
app = FastAPI(title="FastAPI 第八课")


class ItemInput(BaseModel):
    content: str


def create_tables(connection: sqlite3.Connection) -> None:
    connection.execute(
        "CREATE TABLE IF NOT EXISTS items "
        "(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL)"
    )
    connection.commit()


def get_connection() -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        create_tables(connection)
        yield connection
    finally:
        connection.close()


@app.get("/items")
def list_items(
    limit: int = Query(default=10, ge=1, le=100),
    connection: sqlite3.Connection = Depends(get_connection),
):
    rows = connection.execute(
        "SELECT id, content FROM items ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


@app.post("/items", status_code=201)
def create_item(
    item: ItemInput,
    connection: sqlite3.Connection = Depends(get_connection),
):
    cursor = connection.execute(
        "INSERT INTO items (content) VALUES (?)",
        (item.content,),
    )
    connection.commit()
    return {"id": cursor.lastrowid, "content": item.content}


@app.get("/items/{item_id}")
def get_item(
    item_id: int,
    connection: sqlite3.Connection = Depends(get_connection),
):
    row = connection.execute(
        "SELECT id, content FROM items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="事项不存在")
    return dict(row)


def create_test_connection(database: Path) -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    try:
        create_tables(connection)
        yield connection
    finally:
        connection.close()


@pytest.fixture
def client(tmp_path: Path) -> Generator[TestClient, None, None]:
    test_database = tmp_path / "test.sqlite3"

    def override_get_connection():
        yield from create_test_connection(test_database)

    app.dependency_overrides[get_connection] = override_get_connection
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def test_create_and_get_item(client: TestClient) -> None:
    response = client.post("/items", json={"content": "学习接口测试"})

    assert response.status_code == 201
    item_id = response.json()["id"]

    response = client.get(f"/items/{item_id}")

    assert response.status_code == 200
    assert response.json()["content"] == "学习接口测试"


def test_invalid_limit_returns_422(client: TestClient) -> None:
    response = client.get("/items?limit=0")

    assert response.status_code == 422


def test_missing_item_returns_404(client: TestClient) -> None:
    response = client.get("/items/999")

    assert response.status_code == 404


# ===== 课后作业 =====

def homework() -> None:
    """作业要求写在课件中；默认入口不执行作业。"""
    raise NotImplementedError("请根据课件完成作业")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("lesson08_testing:app", host="127.0.0.1", port=8007, reload=True)
