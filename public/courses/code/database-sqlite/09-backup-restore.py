"""第九课：SQLite 备份、恢复与完整性检查。"""

import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).parent
DATABASE = BASE_DIR / "09-backup-restore.sqlite3"
BACKUP = BASE_DIR / "09-backup-restore_backup.sqlite3"
VACUUM_BACKUP = BASE_DIR / "09-backup-restore_vacuum_backup.sqlite3"


def remove_if_exists(path: Path) -> None:
    if path.exists():
        path.unlink()


def main() -> None:
    remove_if_exists(DATABASE)
    remove_if_exists(BACKUP)
    remove_if_exists(VACUUM_BACKUP)

    connection = sqlite3.connect(DATABASE)
    try:
        connection.executescript(
            """
            CREATE TABLE notes (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                body TEXT NOT NULL
            );

            INSERT INTO notes (title, body)
            VALUES ('SQLite', 'file database'),
                   ('Backup', 'restore and verify');
            """
        )
        connection.commit()

        print("journal mode:", connection.execute("PRAGMA journal_mode").fetchone()[0])
        print("integrity:", connection.execute("PRAGMA integrity_check").fetchone()[0])
        print("quick check:", connection.execute("PRAGMA quick_check").fetchone()[0])

        # 方式一：VACUUM INTO 生成新的数据库文件。
        connection.execute("VACUUM INTO ?", (str(VACUUM_BACKUP),))

        # 方式二：使用 SQLite Online Backup API。
        backup_connection = sqlite3.connect(BACKUP)
        try:
            with backup_connection:
                connection.backup(backup_connection)
        finally:
            backup_connection.close()
    finally:
        connection.close()

    # 在临时副本上验证，而不是直接覆盖原文件。
    restored = sqlite3.connect(BACKUP)
    try:
        print("backup integrity:", restored.execute("PRAGMA integrity_check").fetchone()[0])
        print("restored notes:", restored.execute("SELECT COUNT(*) FROM notes").fetchone()[0])
    finally:
        restored.close()


if __name__ == "__main__":
    main()
