# 第 3 课：多阶段 + 非 root + HEALTHCHECK
# 构建：
#   docker build -f code/docker/03-app-hardened.Dockerfile -t takeout-api:2 code/docker
# 运行：
#   docker run --rm -p 8000:8000 takeout-api:2
#
# 说明：本例用 orjson 作为第三方依赖，builder 阶段把依赖构建成 wheel，
# 运行阶段只复制 wheel 并安装，不把构建工具带进最终镜像。

FROM python:3.12 AS builder

WORKDIR /build

COPY 03-requirements.txt requirements.txt
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/*.whl \
    && rm -rf /wheels

# 创建非 root 用户；容器默认不再以 root 运行
RUN groupadd --system app \
    && useradd --system --gid app --no-create-home app

COPY --chown=app:app 03-minimal-app.py app.py

ENV APP_ENV=prod \
    PORT=8000 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

USER app

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health').read()"

CMD ["python", "app.py"]
