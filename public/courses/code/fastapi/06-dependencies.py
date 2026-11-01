import sqlite3
from pathlib import Path
from typing import Annotated, Generator

from fastapi import Depends, FastAPI, Query, status
from pydantic import BaseModel


DATABASE = Path(__file__).parent / "study.sqlite3"
app = FastAPI(title="FastAPI 第六课")


class ItemInput(BaseModel):
    content: str


def setup_database() -> None:
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS items "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL)"
        )


def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """为当前请求提供连接，并在请求结束时关闭连接。"""
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def get_limit(
    limit: int = Query(default=10, ge=1, le=100),
) -> int:
    """演示一个返回普通值的可复用依赖。"""
    return limit


setup_database()


@app.get("/items")
def list_items(
    limit: Annotated[int, Depends(get_limit)],
    connection: Annotated[sqlite3.Connection, Depends(get_connection)],
):
    rows = connection.execute(
        "SELECT id, content FROM items ORDER BY id LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(
    item: ItemInput,
    connection: Annotated[sqlite3.Connection, Depends(get_connection)],
):
    cursor = connection.execute(
        "INSERT INTO items (content) VALUES (?)",
        (item.content,),
    )
    connection.commit()
    return {"id": cursor.lastrowid, "content": item.content}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8005)
