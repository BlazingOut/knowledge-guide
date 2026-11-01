"""第 7 课：外卖系统 API（综合练习）。

这个 FastAPI 应用真正连接 MySQL 和 Redis：

    GET  /                 服务信息
    GET  /health           健康检查
    POST /orders           创建订单（写 MySQL，Redis 计数）
    GET  /orders           查询最近订单（读 MySQL）
    GET  /orders/count     查看 Redis 里的订单计数

通过环境变量配置：

    MYSQL_HOST / MYSQL_PORT / MYSQL_USER / MYSQL_PASSWORD / MYSQL_DATABASE
    REDIS_HOST / REDIS_PORT

运行方式（本机直接跑，需要本地 MySQL/Redis）：

    python 07-main.py

Docker 里由 CMD 启动：uvicorn.run(app, host="0.0.0.0", port=PORT)
"""

import os
import time

import pymysql
import redis
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="takeout-api")

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "example")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "takeout")

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

PORT = int(os.getenv("PORT", "8000"))


class OrderIn(BaseModel):
    user_id: int
    amount: float


def get_db() -> pymysql.Connection:
    """打开一个 MySQL 连接。"""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        autocommit=True,
        connect_timeout=5,
    )


def get_redis() -> redis.Redis:
    """返回一个 Redis 客户端。"""
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=3,
    )


def wait_for_deps(retries: int = 30) -> None:
    """启动前等待 MySQL 和 Redis 就绪，避免容器一启动就连接失败。"""
    last_error = None
    for _ in range(retries):
        try:
            conn = get_db()
            conn.close()
            r = get_redis()
            r.ping()
            return
        except Exception as exc:  # 依赖还没就绪，继续重试
            last_error = exc
            time.sleep(1)
    raise RuntimeError(f"依赖未就绪: {last_error}")


@app.get("/")
def index() -> dict:
    return {
        "service": "takeout-api",
        "mysql_host": MYSQL_HOST,
        "redis_host": REDIS_HOST,
    }


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/orders")
def create_order(order: OrderIn) -> dict:
    if order.amount <= 0:
        raise HTTPException(status_code=422, detail="amount must be positive")

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO orders (user_id, amount) VALUES (%s, %s)",
                (order.user_id, order.amount),
            )
            order_id = cur.lastrowid
    finally:
        conn.close()

    r = get_redis()
    r.incr("orders:count")

    return {"id": order_id, "user_id": order.user_id, "amount": order.amount}


@app.get("/orders")
def list_orders() -> dict:
    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, user_id, amount, status, created_at "
                "FROM orders ORDER BY id DESC LIMIT 10"
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    orders = [
        {
            "id": row[0],
            "user_id": row[1],
            "amount": float(row[2]),
            "status": row[3],
            "created_at": str(row[4]),
        }
        for row in rows
    ]
    return {"orders": orders}


@app.get("/orders/count")
def order_count() -> dict:
    r = get_redis()
    return {"count": int(r.get("orders:count") or 0)}


def main() -> None:
    wait_for_deps()
    uvicorn.run(app, host="0.0.0.0", port=PORT)


if __name__ == "__main__":
    main()
