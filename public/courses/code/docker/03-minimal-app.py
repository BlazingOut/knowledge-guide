"""第 3 课：外卖系统 API 的最小骨架。

这个文件只用于演示 Dockerfile 构建，业务数据是假的：
    GET /         返回服务信息
    GET /orders   返回一条示例订单
    GET /health   返回健康状态

真实外卖系统会把订单写进 MySQL、把缓存/会话放进 Redis；
本课先把 app 镜像构建讲清楚，连接多服务放在后续课程。

运行方式：
    python 03-minimal-app.py

    # macOS / Linux
    PORT=8000 APP_ENV=dev python 03-minimal-app.py

    # Windows PowerShell
    $env:PORT=8000; $env:APP_ENV=dev; python 03-minimal-app.py

如果安装了 orjson，就使用 orjson 序列化；否则回退到标准库 json。
这样可以直接观察多阶段镜像里依赖是否装进了最终镜像。
"""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os

try:
    import orjson
except ImportError:  # 单阶段示例没有安装依赖，回退到标准库
    orjson = None

APP_ENV = os.getenv("APP_ENV", "dev")
PORT = int(os.getenv("PORT", "8000"))


def to_json(payload: dict) -> bytes:
    """把 dict 序列化成 UTF-8 JSON 字节。"""
    if orjson is not None:
        return orjson.dumps(payload)
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


class Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/health":
            payload = {"status": "ok"}
        elif self.path == "/orders":
            payload = {
                "orders": [
                    {"id": 1, "status": "created", "amount": 38.5},
                ]
            }
        elif self.path == "/":
            payload = {
                "service": "takeout-api",
                "env": APP_ENV,
                "json": "orjson" if orjson is not None else "stdlib",
            }
        else:
            self.send_error(404, "Not Found")
            return

        body = to_json(payload)
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt: str, *args) -> None:
        print(fmt % args, flush=True)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"listening on 0.0.0.0:{PORT}, env={APP_ENV}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
