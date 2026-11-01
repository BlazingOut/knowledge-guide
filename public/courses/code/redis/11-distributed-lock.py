"""第 11 课：Redis 分布式锁的基本模型。"""

from __future__ import annotations

import time
import uuid

import redis


RELEASE_LOCK_SCRIPT = """
if redis.call("GET", KEYS[1]) == ARGV[1] then
    return redis.call("DEL", KEYS[1])
end
return 0
"""


def lock_key(task_id: str) -> str:
    return f"course:lesson09:lock:task:{task_id}"


def acquire_lock(client: redis.Redis, key: str, token: str, ttl: int) -> bool:
    return bool(client.set(key, token, nx=True, ex=ttl))


def release_lock(client: redis.Redis, key: str, token: str) -> bool:
    deleted = client.eval(RELEASE_LOCK_SCRIPT, 1, key, token)
    return bool(deleted)


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    key = lock_key("9001")
    client.delete(key)

    worker_a = str(uuid.uuid4())
    worker_b = str(uuid.uuid4())

    print("Worker A acquired:", acquire_lock(client, key, worker_a, ttl=10))
    print("Worker B acquired:", acquire_lock(client, key, worker_b, ttl=10))

    time.sleep(0.1)
    print("Worker B releases A lock:", release_lock(client, key, worker_b))
    print("Worker A releases lock:", release_lock(client, key, worker_a))

    client.delete(key)


if __name__ == "__main__":
    main()
