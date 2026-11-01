"""第 7 课：缓存穿透、击穿和雪崩的基础防护。"""

from __future__ import annotations

import json
import random

import redis


DATABASE = {
    42: {"id": 42, "title": "Redis 入门"},
}
MISSING = "__missing__"


def article_key(article_id: int) -> str:
    return f"course:lesson05:article:{article_id}"


def read_article(client: redis.Redis, article_id: int) -> dict | None:
    if article_id <= 0:
        return None

    key = article_key(article_id)
    cached = client.get(key)
    if cached == MISSING:
        return None
    if cached is not None:
        return json.loads(cached)

    article = DATABASE.get(article_id)
    if article is None:
        client.set(key, MISSING, ex=30)
        return None

    ttl = 300 + random.randint(0, 60)
    client.set(key, json.dumps(article, ensure_ascii=False), ex=ttl)
    return article


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    existing_key = article_key(42)
    missing_key = article_key(999999)
    client.delete(existing_key, missing_key)

    print("Existing article:", read_article(client, 42))
    print("Missing article:", read_article(client, 999999))
    print("Missing article from cache:", read_article(client, 999999))
    print("Existing TTL:", client.ttl(existing_key))
    print("Missing TTL:", client.ttl(missing_key))

    client.delete(existing_key, missing_key)


if __name__ == "__main__":
    main()
