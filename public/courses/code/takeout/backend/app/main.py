"""外卖课程第 2 课：最小 FastAPI 应用。

只提供健康检查和连通性检查，业务代码从第 3 课开始。
连接信息全部从环境变量读取（由 docker-compose.yml 注入）。
"""

import os

import pymysql
import redis
from fastapi import FastAPI

app = FastAPI(title="takeout", version="0.1.0")


def redis_ok() -> bool:
    """检查 Redis 是否连通。"""
    try:
        client = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        return client.ping()
    except Exception:
        return False


def mysql_ok() -> bool:
    """检查 MySQL 是否连通。"""
    try:
        conn = pymysql.connect(
            host=os.getenv("MYSQL_HOST", "localhost"),
            port=int(os.getenv("MYSQL_PORT", "3306")),
            user=os.getenv("MYSQL_USER", "takeout"),
            password=os.getenv("MYSQL_PASSWORD", ""),
            database=os.getenv("MYSQL_DATABASE", "takeout"),
            connect_timeout=1,
        )
        conn.close()
        return True
    except Exception:
        return False


@app.get("/health")
def health() -> dict:
    """应用本身是否活着。"""
    return {"status": "ok"}


@app.get("/api/ping")
def ping() -> dict:
    """连通性检查：网关 -> 应用 -> MySQL / Redis 是否都通。"""
    return {"redis": redis_ok(), "mysql": mysql_ok()}


# ===== 课后作业 =====
# 作业：新增 GET /api/services，返回每个服务的详细状态和错误信息。
# 要求：组合本课两个要点（MySQL 连接检查 + Redis 连接检查），
#       返回值形如 {"redis": "ok", "mysql": "pymysql err ..."}。
# 提示：把上面的 redis_ok / mysql_ok 改成返回错误信息字符串，再组合成一个接口。
# 完成后：docker compose restart backend，curl 验证。
