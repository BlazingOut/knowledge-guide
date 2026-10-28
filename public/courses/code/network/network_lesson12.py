import http.client
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit


UPSTREAM_HOST = "127.0.0.1"
UPSTREAM_PORT = 9101
GATEWAY_HOST = "127.0.0.1"
GATEWAY_PORT = 9100


class UpstreamHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/answer":
            self.send_error(404, "not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        message = payload.get("message", "")
        response = {"answer": f"上游服务收到：{message}"}
        body = json.dumps(response, ensure_ascii=False).encode("utf-8")

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        print(f"[upstream] {format % args}")


class GatewayHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/chat":
            self.send_error(404, "not found")
            return

        length = int(self.headers.get("Content-Length", "0"))
        request_body = self.rfile.read(length)
        try:
            upstream = http.client.HTTPConnection(
                UPSTREAM_HOST,
                UPSTREAM_PORT,
                timeout=3,
            )
            upstream.request(
                "POST",
                "/answer",
                body=request_body,
                headers={"Content-Type": "application/json"},
            )
            upstream_response = upstream.getresponse()
            response_body = upstream_response.read()
        except (ConnectionRefusedError, TimeoutError, OSError) as error:
            self.send_error(502, f"upstream error: {error}")
            return
        finally:
            if "upstream" in locals():
                upstream.close()

        self.send_response(upstream_response.status)
        self.send_header(
            "Content-Type",
            upstream_response.getheader("Content-Type", "application/json"),
        )
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def log_message(self, format, *args):
        print(f"[gateway] {format % args}")


def start_server(server: ThreadingHTTPServer) -> threading.Thread:
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return thread


def call_gateway(message: str) -> None:
    connection = http.client.HTTPConnection(
        GATEWAY_HOST,
        GATEWAY_PORT,
        timeout=3,
    )
    body = json.dumps({"message": message}, ensure_ascii=False)
    connection.request(
        "POST",
        "/chat",
        body=body.encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    response = connection.getresponse()
    print(f"client <- {response.status}: {response.read().decode('utf-8')}")
    connection.close()


def main() -> None:
    upstream = ThreadingHTTPServer(
        (UPSTREAM_HOST, UPSTREAM_PORT),
        UpstreamHandler,
    )
    gateway = ThreadingHTTPServer(
        (GATEWAY_HOST, GATEWAY_PORT),
        GatewayHandler,
    )
    start_server(upstream)
    start_server(gateway)
    print(f"upstream: http://{UPSTREAM_HOST}:{UPSTREAM_PORT}")
    print(f"gateway:  http://{GATEWAY_HOST}:{GATEWAY_PORT}")

    try:
        call_gateway("请解释一次请求经过了什么")
        print("按 Ctrl+C 停止服务")
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        gateway.shutdown()
        upstream.shutdown()
        gateway.server_close()
        upstream.server_close()


# ===== 课后作业 =====

def homework() -> None:
    """请根据课件完成故障注入和排查练习。"""
    raise NotImplementedError("请根据课件完成作业")


if __name__ == "__main__":
    main()
