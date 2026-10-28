"""第七课：SQLite 的索引与查询计划。"""

import sqlite3
from pathlib import Path


DATABASE = Path(__file__).with_name("database_lesson07.sqlite3")


def print_plan(connection: sqlite3.Connection, title: str, sql: str, parameters=()) -> None:
    rows = connection.execute(f"EXPLAIN QUERY PLAN {sql}", parameters).fetchall()
    print(f"\n--- {title} ---")
    for row in rows:
        print(tuple(row))


def main() -> None:
    connection = sqlite3.connect(DATABASE)
    try:
        connection.executescript(
            """
            DROP TABLE IF EXISTS products;
            DROP TABLE IF EXISTS orders;

            CREATE TABLE products (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                price INTEGER NOT NULL,
                stock INTEGER
            );

            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                order_no TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            """
        )
        connection.executemany(
            "INSERT INTO products (id, name, category, price, stock) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "键盘", "办公", 199, 20),
                (2, "鼠标", "办公", 99, 0),
                (3, "显示器", "办公", 1299, 8),
                (4, "水杯", "生活", 59, 30),
                (5, "背包", "生活", 299, 5),
                (6, "耳机", "数码", 499, None),
            ],
        )
        connection.executemany(
            """
            INSERT INTO orders (id, user_id, order_no, status, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            [
                (1, 1, "ORD-001", "paid", "2026-01-01 10:00:00"),
                (2, 1, "ORD-002", "pending", "2026-01-02 10:00:00"),
                (3, 2, "ORD-003", "paid", "2026-01-03 10:00:00"),
            ],
        )
        connection.commit()

        print_plan(
            connection,
            "没有索引时的分类查询",
            "SELECT id, name, price FROM products WHERE category = ?",
            ("办公",),
        )

        connection.execute(
            "CREATE INDEX idx_products_category ON products(category)"
        )
        print_plan(
            connection,
            "使用分类索引",
            "SELECT id, name, price FROM products WHERE category = ?",
            ("办公",),
        )

        connection.execute(
            "CREATE INDEX idx_products_category_name ON products(category, name)"
        )
        print_plan(
            connection,
            "观察覆盖索引",
            "SELECT category, name FROM products WHERE category = ?",
            ("办公",),
        )

        connection.execute(
            "CREATE INDEX idx_orders_user_status ON orders(user_id, status)"
        )
        print_plan(
            connection,
            "联合索引匹配前面的列",
            "SELECT id, order_no FROM orders WHERE user_id = ? AND status = ?",
            (1, "paid"),
        )
        print_plan(
            connection,
            "只使用联合索引的后面列",
            "SELECT id, order_no FROM orders WHERE status = ?",
            ("paid",),
        )

        connection.execute("ANALYZE")
        print_plan(
            connection,
            "ANALYZE 后再次观察",
            "SELECT id, name FROM products WHERE category = ?",
            ("办公",),
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
