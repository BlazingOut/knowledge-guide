# 第 7 课：外卖系统 app 的多阶段 Dockerfile
# 构建：
#   docker build -f code/docker/07-app.Dockerfile -t takeout-api:3 code/docker
# 运行（需要先启动 MySQL 和 Redis）：
#   docker run -d --name takeout-api -p 8000:8000 -e MYSQL_HOST=... -e REDIS_HOST=... takeout-api:3

FROM python:3.12 AS builder

WORKDIR /build
COPY 07-requirements.txt requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

RUN groupadd --system app \
    && useradd --system --gid app --no-create-home app

COPY --chown=app:app 07-main.py app.py

ENV APP_ENV=prod \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

CMD ["python", "app.py"]
