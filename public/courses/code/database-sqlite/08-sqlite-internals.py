"""第八课：SQLite 特有语法与内部结构。"""

import sqlite3
from pathlib import Path


DATABASE = Path(__file__).with_name("08-sqlite-internals.sqlite3")


def main() -> None:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        connection.executescript(
            """
            DROP TABLE IF EXISTS settings;
            DROP TABLE IF EXISTS events;
            DROP TABLE IF EXISTS user_tenants;
            DROP TABLE IF EXISTS documents;
            DROP TABLE IF EXISTS notes_fts;

            CREATE TABLE settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE TABLE events (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL
            );

            CREATE TABLE user_tenants (
                user_id INTEGER NOT NULL,
                tenant_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                PRIMARY KEY (user_id, tenant_id)
            ) WITHOUT ROWID;

            CREATE TABLE documents (
                id INTEGER PRIMARY KEY,
                data TEXT NOT NULL
            );
            """
        )

        connection.execute("INSERT INTO events (name) VALUES (?)", ("created",))
        row = connection.execute(
            "SELECT id, rowid, _rowid_, name FROM events"
        ).fetchone()
        print("rowid aliases:", dict(row))

        row = connection.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            RETURNING rowid, key, value
            """,
            ("theme", "dark"),
        ).fetchone()
        print("RETURNING insert:", dict(row))

        row = connection.execute(
            """
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            RETURNING key, value
            """,
            ("theme", "light"),
        ).fetchone()
        print("UPSERT:", dict(row))

        connection.execute(
            "INSERT INTO documents (data) VALUES (?)",
            ('{"name":"Alice","role":"admin"}',),
        )
        json_row = connection.execute(
            "SELECT json_extract(data, '$.name') AS name FROM documents"
        ).fetchone()
        print("JSON1:", dict(json_row))

        try:
            connection.execute(
                """
                CREATE VIRTUAL TABLE notes_fts
                USING fts5(title, body)
                """
            )
            connection.execute(
                "INSERT INTO notes_fts (title, body) VALUES (?, ?)",
                ("SQLite", "SQLite is a file database"),
            )
            rows = connection.execute(
                "SELECT title FROM notes_fts WHERE notes_fts MATCH ?",
                ("SQLite",),
            ).fetchall()
            print("FTS5:", [dict(row) for row in rows])
        except sqlite3.OperationalError as error:
            print("FTS5 unavailable in this SQLite build:", error)

        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
