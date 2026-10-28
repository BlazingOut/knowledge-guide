"""第 2 课：Redis 常见数据结构。"""

from __future__ import annotations

import redis


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    prefix = "course:lesson02:"

    client.set(prefix + "message", "hello")
    print("String:", client.get(prefix + "message"))

    client.hset(
        prefix + "user:1001",
        mapping={"name": "Alice", "level": "3"},
    )
    print("Hash:", client.hgetall(prefix + "user:1001"))

    client.rpush(prefix + "tasks", "task-1", "task-2")
    print("List:", client.lrange(prefix + "tasks", 0, -1))

    client.sadd(prefix + "tags", "python", "redis", "python")
    print("Set:", sorted(client.smembers(prefix + "tags")))

    client.zadd(
        prefix + "leaderboard",
        {"user:1001": 98, "user:1002": 85},
    )
    print(
        "Sorted Set:",
        client.zrevrange(prefix + "leaderboard", 0, -1, withscores=True),
    )

    for key in client.scan_iter(match=prefix + "*"):
        client.delete(key)


if __name__ == "__main__":
    main()
