import sqlite3
from pathlib import Path
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

DATABASE = Path(__file__).parent / "study.sqlite3"
app = FastAPI(title="FastAPI 第五课")

class ItemInput(BaseModel):
    content: str

def setup_database() -> None:
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS items (id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL)")

setup_database()

@app.get("/items")
def list_items():
    with sqlite3.connect(DATABASE) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute("SELECT id, content FROM items ORDER BY id").fetchall()
        return [dict(row) for row in rows]

@app.post("/items", status_code=status.HTTP_201_CREATED)
def create_item(item: ItemInput):
    with sqlite3.connect(DATABASE) as connection:
        cursor = connection.execute("INSERT INTO items (content) VALUES (?)", (item.content,))
        return {"id": cursor.lastrowid, "content": item.content}

@app.get("/items/{item_id}")
def get_item(item_id: int):
    with sqlite3.connect(DATABASE) as connection:
        row = connection.execute("SELECT id, content FROM items WHERE id = ?", (item_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="事项不存在")
        return {"id": row[0], "content": row[1]}


# TODO 作业 1：给 create_item 的返回结果增加一条固定的说明文字。
# TODO 作业 2：修改说明文字后，通过 /docs 创建一条事项。
# TODO 作业 3：用 GET /items 确认新事项仍然能被查询出来。
# TODO 作业 4：用 GET /items/{item_id} 查询刚创建的事项。
# TODO 作业 5：查询一个不存在的 ID，确认仍然返回 404。


# ===== 直接运行 =====
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8004)
