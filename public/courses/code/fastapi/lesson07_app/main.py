import sqlite3

from fastapi import FastAPI

from .config import DATABASE
from .routers.items import router as items_router


def setup_database() -> None:
    with sqlite3.connect(DATABASE) as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS items "
            "(id INTEGER PRIMARY KEY AUTOINCREMENT, content TEXT NOT NULL)"
        )


setup_database()
app = FastAPI(title="FastAPI 第七课")
app.include_router(items_router)
