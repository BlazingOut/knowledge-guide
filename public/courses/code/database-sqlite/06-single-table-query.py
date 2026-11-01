import sqlite3
from pathlib import Path


DATABASE = Path(__file__).parent / "06-single-table-query.sqlite3"


def setup_database(connection: sqlite3.Connection) -> None:
    connection.execute("DROP TABLE IF EXISTS products")
    connection.execute(
        """
        CREATE TABLE products (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price INTEGER NOT NULL,
            stock INTEGER,
            description TEXT
        )
        """
    )
    connection.executemany(
        """
        INSERT INTO products
            (id, name, category, price, stock, description)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (1, "键盘", "办公", 199, 20, "机械键盘"),
            (2, "鼠标", "办公", 99, 0, "无线鼠标"),
            (3, "显示器", "办公", 1299, 8, "27 英寸显示器"),
            (4, "水杯", "生活", 59, 30, None),
            (5, "背包", "生活", 299, 5, "通勤背包"),
            (6, "耳机", "数码", 499, None, "降噪耳机"),
        ],
    )
    connection.commit()


def print_rows(title: str, rows: list[sqlite3.Row]) -> None:
    print(f"\n--- {title} ---")
    for row in rows:
        print(dict(row))


def main() -> None:
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    try:
        setup_database(connection)

        rows = connection.execute(
            """
            SELECT id, name, category
            FROM products
            WHERE category IN (?, ?)
            ORDER BY id
            """,
            ("办公", "数码"),
        ).fetchall()
        print_rows("IN：属于指定分类", rows)

        categories = ["办公", "数码", "生活"]
        placeholders = ", ".join("?" for _ in categories)
        rows = connection.execute(
            f"""
            SELECT id, name, category
            FROM products
            WHERE category IN ({placeholders})
            ORDER BY id
            """,
            categories,
        ).fetchall()
        print_rows("动态 IN：根据候选数量生成占位符", rows)

        rows = connection.execute(
            """
            SELECT name, price
            FROM products
            WHERE price BETWEEN ? AND ?
            ORDER BY price
            """,
            (100, 500),
        ).fetchall()
        print_rows("BETWEEN：价格范围", rows)

        rows = connection.execute(
            """
            SELECT name
            FROM products
            WHERE name LIKE ?
            ORDER BY id
            """,
            ("%器%",),
        ).fetchall()
        print_rows("LIKE：名称包含“器”", rows)

        rows = connection.execute(
            """
            SELECT name, stock
            FROM products
            WHERE stock IS NULL
            ORDER BY id
            """
        ).fetchall()
        print_rows("IS NULL：库存尚未记录", rows)

        rows = connection.execute(
            """
            SELECT DISTINCT category
            FROM products
            ORDER BY category
            """
        ).fetchall()
        print_rows("DISTINCT：不同分类", rows)

        rows = connection.execute(
            """
            SELECT name, category, price, stock
            FROM products
            WHERE (category = ? OR category = ?)
              AND price < ?
            ORDER BY price
            LIMIT ? OFFSET ?
            """,
            ("办公", "生活", 500, 2, 0),
        ).fetchall()
        print_rows("括号、LIMIT 和 OFFSET", rows)
    finally:
        connection.close()


# ===== 课后作业 =====

def homework(connection: sqlite3.Connection) -> None:
    """作业要求写在课件中；默认入口不执行作业。"""
    raise NotImplementedError("请根据课件完成作业")


if __name__ == "__main__":
    main()
