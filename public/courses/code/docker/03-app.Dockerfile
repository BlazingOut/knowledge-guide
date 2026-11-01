# 第 3 课：最小单阶段 Dockerfile
# 构建：
#   docker build -f code/docker/03-app.Dockerfile -t takeout-api:1 code/docker
# 运行：
#   docker run --rm -p 8000:8000 takeout-api:1

FROM python:3.12-slim

WORKDIR /app

COPY 03-minimal-app.py app.py

ENV APP_ENV=dev \
    PORT=8000

EXPOSE 8000

CMD ["python", "app.py"]
