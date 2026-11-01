"""第 8 课：缓存与数据库一致性的基本更新流程。"""

from __future__ import annotations

import json

import redis


DATABASE = {
    42: {"id": 42, "title": "Redis 入门"},
}


def article_key(article_id: int) -> str:
    return f"course:lesson06:article:{article_id}"


def read_article(client: redis.Redis, article_id: int) -> dict | None:
    key = article_key(article_id)
    cached = client.get(key)
    if cached is not None:
        print("cache hit")
        return json.loads(cached)

    print("cache miss")
    article = DATABASE.get(article_id)
    if article is None:
        return None

    client.set(key, json.dumps(article, ensure_ascii=False), ex=60)
    return article.copy()


def update_article(client: redis.Redis, article_id: int, title: str) -> None:
    article = DATABASE.get(article_id)
    if article is None:
        raise KeyError(article_id)

    article["title"] = title
    client.delete(article_key(article_id))


def main() -> None:
    client = redis.Redis(
        host="127.0.0.1",
        port=6379,
        db=0,
        decode_responses=True,
    )
    client.ping()

    key = article_key(42)
    client.delete(key)

    print("Initial read:", read_article(client, 42))
    print("Cached read:", read_article(client, 42))

    update_article(client, 42, "Redis 一致性")
    print("After database update and cache delete:", read_article(client, 42))

    client.delete(key)


if __name__ == "__main__":
    main()
