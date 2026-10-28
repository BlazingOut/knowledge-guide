import sqlite3
from typing import Annotated, Generator

from fastapi import Depends

from .config import DATABASE
from .store import ItemStore


def get_connection() -> Generator[sqlite3.Connection, None, None]:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
    finally:
        connection.close()


def get_store(
    connection: Annotated[sqlite3.Connection, Depends(get_connection)],
) -> ItemStore:
    return ItemStore(connection)
