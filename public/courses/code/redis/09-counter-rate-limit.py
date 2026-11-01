"""第 9 课：Redis 计数器、原子操作与固定窗口限流。"""

from __future__ import annotations

import time

import redis


def rate_limit(
    client: redis.Redis,
    user_id: int,
    limit: int,
    window_seconds: int,
) -> tuple[bool, int]:
    window = int(time.time()) // window_seconds
    key = f"course:lesson07:rate:{user_id}:{window}"

    created = client.set(key, 1, ex=window_seconds, nx=True)
    if created:
        count = 1
    else:
        count = client.incr(key)

    return count <= limit, count


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    counter_key = "course:lesson07:counter"
    client.delete(counter_key)
    print("Counter:", client.incr(counter_key))
    print("Counter:", client.incrby(counter_key, 4))
    print("Counter TTL before expiry:", client.ttl(counter_key))

    user_id = 1001
    for request_number in range(1, 6):
        allowed, count = rate_limit(
            client,
            user_id=user_id,
            limit=3,
            window_seconds=60,
        )
        print(
            f"Request {request_number}:",
            "allowed" if allowed else "rejected",
            f"count={count}",
        )

    client.delete(counter_key)
    for key in client.scan_iter(match="course:lesson07:rate:*"):
        client.delete(key)


if __name__ == "__main__":
    main()
