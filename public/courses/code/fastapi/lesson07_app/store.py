import sqlite3


class ItemStore:
    """只负责把事项操作转换成 SQL。"""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def list_items(self, limit: int = 10) -> list[dict[str, object]]:
        rows = self.connection.execute(
            "SELECT id, content FROM items ORDER BY id LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def create_item(self, content: str) -> dict[str, object]:
        cursor = self.connection.execute(
            "INSERT INTO items (content) VALUES (?)",
            (content,),
        )
        self.connection.commit()
        return {"id": cursor.lastrowid, "content": content}
