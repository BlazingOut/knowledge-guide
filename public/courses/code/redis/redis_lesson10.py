"""第 8 课：使用 Redis 保存幂等请求状态。"""

from __future__ import annotations

import json

import redis


def request_key(request_id: str) -> str:
    return f"course:lesson08:idempotency:{request_id}"


def create_task(client: redis.Redis, request_id: str, title: str) -> dict:
    key = request_key(request_id)
    existing = client.get(key)
    if existing is not None:
        state = json.loads(existing)
        if state["title"] != title:
            raise ValueError("request_id was reused with different input")
        return state

    processing = {
        "status": "processing",
        "request_id": request_id,
        "title": title,
    }
    created = client.set(key, json.dumps(processing), nx=True, ex=300)
    if not created:
        return {"status": "processing", "request_id": request_id}

    result = {
        "status": "succeeded",
        "request_id": request_id,
        "title": title,
        "task_id": f"task:{request_id}",
    }
    client.set(key, json.dumps(result), ex=300)
    return result


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    request_id = "request-1001"
    key = request_key(request_id)
    client.delete(key)

    print("First request:", create_task(client, request_id, "send report"))
    print("Retry request:", create_task(client, request_id, "send report"))

    try:
        create_task(client, request_id, "different input")
    except ValueError as error:
        print("Conflicting retry:", error)

    client.delete(key)


if __name__ == "__main__":
    main()
