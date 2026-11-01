"""第 12 课：使用 Redis List 实现最小异步任务流程。"""

from __future__ import annotations

import json

import redis


QUEUE_KEY = "course:lesson10:tasks"
TASK_PREFIX = "course:lesson10:task:"


def task_key(task_id: str) -> str:
    return TASK_PREFIX + task_id


def enqueue_task(client: redis.Redis, task_id: str, title: str) -> None:
    state = {
        "task_id": task_id,
        "status": "pending",
        "title": title,
        "retry_count": 0,
        "error": None,
    }
    client.hset(task_key(task_id), mapping=state)
    client.rpush(QUEUE_KEY, json.dumps({"task_id": task_id}))


def consume_one(client: redis.Redis) -> dict | None:
    item = client.brpop(QUEUE_KEY, timeout=1)
    if item is None:
        return None

    _, payload = item
    task_id = json.loads(payload)["task_id"]
    client.hset(task_key(task_id), "status", "running")

    try:
        client.hset(
            task_key(task_id),
            mapping={"status": "succeeded", "result": "task completed"},
        )
    except redis.RedisError as error:
        client.hset(
            task_key(task_id),
            mapping={"status": "failed", "error": str(error)},
        )

    return {
        "task_id": task_id,
        "state": client.hgetall(task_key(task_id)),
    }


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    task_id = "task-9001"
    client.delete(QUEUE_KEY, task_key(task_id))

    enqueue_task(client, task_id, "generate report")
    print("Before consume:", client.hgetall(task_key(task_id)))
    print("Consumed:", consume_one(client))

    client.delete(QUEUE_KEY, task_key(task_id))


if __name__ == "__main__":
    main()
