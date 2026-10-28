"""第 11 课：消息重试、死信和重复消费的基础示例。"""

from __future__ import annotations

import json

import redis


QUEUE_KEY = "course:lesson11:queue"
DEAD_LETTER_KEY = "course:lesson11:dead-letter"
TASK_PREFIX = "course:lesson11:task:"
MAX_RETRIES = 2


def task_key(task_id: str) -> str:
    return TASK_PREFIX + task_id


def enqueue(client: redis.Redis, task_id: str, title: str) -> None:
    client.hset(
        task_key(task_id),
        mapping={
            "task_id": task_id,
            "title": title,
            "status": "pending",
            "retry_count": 0,
            "last_error": "",
        },
    )
    client.rpush(QUEUE_KEY, task_id)


def consume_once(
    client: redis.Redis,
    task_id: str,
    should_fail: bool,
) -> str:
    key = task_key(task_id)
    task = client.hgetall(key)
    if task.get("status") == "succeeded":
        return "duplicate skipped"

    client.hset(key, "status", "running")
    if should_fail:
        retry_count = int(task.get("retry_count", 0)) + 1
        if retry_count > MAX_RETRIES:
            client.hset(
                key,
                mapping={"status": "failed", "last_error": "permanent failure"},
            )
            client.rpush(DEAD_LETTER_KEY, json.dumps(task))
            return "moved to dead letter"

        client.hset(
            key,
            mapping={
                "status": "retrying",
                "retry_count": retry_count,
                "last_error": "temporary failure",
            },
        )
        client.rpush(QUEUE_KEY, task_id)
        return "retry scheduled"

    client.hset(
        key,
        mapping={"status": "succeeded", "result": "task completed"},
    )
    return "succeeded"


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    task_id = "task-1101"
    keys = [QUEUE_KEY, DEAD_LETTER_KEY, task_key(task_id)]
    for key in keys:
        client.delete(key)

    enqueue(client, task_id, "send report")
    print("First attempt:", consume_once(client, task_id, should_fail=True))
    print("Second attempt:", consume_once(client, task_id, should_fail=False))
    print("Duplicate delivery:", consume_once(client, task_id, should_fail=False))
    print("Final state:", client.hgetall(task_key(task_id)))

    for key in keys:
        client.delete(key)


if __name__ == "__main__":
    main()
