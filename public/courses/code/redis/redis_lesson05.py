"""第 3 课：Key 设计、过期时间与连接池。"""

from __future__ import annotations

import redis


def main() -> None:
    prefix = "course:lesson03:"
    pool = redis.ConnectionPool.from_url(
        "redis://127.0.0.1:6379/0",
        max_connections=5,
        decode_responses=True,
    )
    client = redis.Redis(
        connection_pool=pool,
        socket_connect_timeout=2,
        socket_timeout=2,
    )

    client.ping()

    permanent_key = prefix + "permanent"
    temporary_key = prefix + "temporary"

    client.set(permanent_key, "no expiry")
    client.set(temporary_key, "expires soon", ex=30)

    print("Permanent TTL:", client.ttl(permanent_key))
    print("Temporary TTL:", client.ttl(temporary_key))
    print("Temporary value:", client.get(temporary_key))

    client.delete(permanent_key, temporary_key)


if __name__ == "__main__":
    main()
