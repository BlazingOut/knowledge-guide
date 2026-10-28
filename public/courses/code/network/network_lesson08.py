"""第八课示例：HTTP 基础——报文、方法与状态码。"""

import json
import socket
import sys


HTTP_PORT = 9600


def create_tcp_socket() -> socket.socket:
    """创建 IPv4 + TCP 的 socket。"""
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def start_server_and_client() -> tuple[socket.socket, socket.socket, socket.socket]:
    """在本机准备一对已连接的 socket，返回 (server, client, conn)。"""
    server = create_tcp_socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    client = create_tcp_socket()
    client.connect(("127.0.0.1", port))
    conn, _ = server.accept()
    return server, client, conn


def recv_until(sock: socket.socket, separator: bytes) -> tuple[bytes, bytes]:
    """从 socket 读到出现 separator 为止。

    返回 (separator 之前的部分, separator 之后已经多读到的部分)。
    TCP 是字节流：一次 recv 可能把空行后面的正文也带回来，必须把多读的部分交还给调用方。
    """
    buf = b""
    while separator not in buf:
        chunk = sock.recv(1024)
        if not chunk:
            raise ConnectionError("对方在报文读完之前关闭了连接")
        buf += chunk
    head, rest = buf.split(separator, 1)
    return head, rest


def recv_exact(sock: socket.socket, n: int, already: bytes = b"") -> bytes:
    """精确收满 n 字节。already 是已经多读到的部分（来自 recv_until 的 rest）。"""
    buf = already
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            raise ConnectionError("对方在正文读完之前关闭了连接")
        buf += chunk
    return buf


def demo_get_request() -> None:
    """手写一次 HTTP GET：客户端拼出完整请求报文，服务器手写完整响应报文。"""
    server, client, conn = start_server_and_client()

    # 请求报文四段：请求行、头部、空行、正文（GET 通常没有正文）
    request = (
        b"GET /api/tasks HTTP/1.1\r\n"
        b"Host: 127.0.0.1\r\n"
        b"Accept: application/json\r\n"
        b"Connection: close\r\n"
        b"\r\n"
    )
    print("客户端发出的请求报文：")
    print(request.decode("ascii"))
    client.sendall(request)

    raw_headers, rest = recv_until(conn, b"\r\n\r\n")
    print("服务器读到的请求行和头部：")
    print(raw_headers.decode("ascii"))
    print(f"（空行之后多读到的字节：{rest!r}）")

    request_line = raw_headers.split(b"\r\n", 1)[0].decode("ascii")
    method, path, version = request_line.split(" ")
    print(f"解析结果：方法={method} 路径={path} 版本={version}")

    body = json.dumps({"items": ["买牛奶", "跑步"]}, ensure_ascii=False).encode("utf-8")
    response = (
        b"HTTP/1.1 200 OK\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        + f"Content-Length: {len(body)}\r\n".encode("ascii")
        + b"Connection: close\r\n"
        + b"\r\n"
        + body
    )
    conn.sendall(response)
    # Connection: close 只是 HTTP 头部里的一句话，内核不会因此关闭 TCP。
    # 客户端下面用"读到空字节为止"判断响应结束，必须由我们主动关掉写端，
    # 对端才会收到 FIN（结束标志），recv 才会返回 b""。
    conn.shutdown(socket.SHUT_WR)

    reply = b""
    while True:
        chunk = client.recv(1024)
        if not chunk:
            break
        reply += chunk
    print("客户端收到的完整响应：")
    print(reply.decode("utf-8"))

    client.close()
    conn.close()
    server.close()


def demo_post_with_body() -> None:
    """手写一次 HTTP POST：正文是 JSON，长度写在 Content-Length 里。"""
    server, client, conn = start_server_and_client()

    payload = json.dumps({"content": "买牛奶"}, ensure_ascii=False).encode("utf-8")
    request = (
        b"POST /api/tasks HTTP/1.1\r\n"
        b"Host: 127.0.0.1\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        + f"Content-Length: {len(payload)}\r\n".encode("ascii")
        + b"Connection: close\r\n"
        + b"\r\n"
        + payload
    )
    print("客户端发出的 POST 请求（含正文）：")
    print(request.decode("utf-8"))
    client.sendall(request)

    raw_headers, rest = recv_until(conn, b"\r\n\r\n")
    headers: dict[str, str] = {}
    for line in raw_headers.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        headers[name.decode("ascii").lower()] = value.strip().decode("ascii")
    length = int(headers["content-length"])
    body = recv_exact(conn, length, already=rest)
    print(f"服务器解析出的正文（{length} 字节）：{body.decode('utf-8')}")

    reply_body = json.dumps({"id": 1, "ok": True}, ensure_ascii=False).encode("utf-8")
    response = (
        b"HTTP/1.1 201 Created\r\n"
        b"Content-Type: application/json; charset=utf-8\r\n"
        + f"Content-Length: {len(reply_body)}\r\n".encode("ascii")
        + b"Connection: close\r\n"
        + b"\r\n"
        + reply_body
    )
    conn.sendall(response)

    # POST 演示走另一条路：不关连接，靠 Content-Length 精确收齐。
    # 这正是长连接能复用同一条 TCP 连接的前提——每条消息自己知道自己有多长。
    raw_reply_headers, reply_rest = recv_until(client, b"\r\n\r\n")
    reply_headers: dict[str, str] = {}
    for line in raw_reply_headers.split(b"\r\n")[1:]:
        name, _, value = line.partition(b":")
        reply_headers[name.decode("ascii").lower()] = value.strip().decode("ascii")
    reply_length = int(reply_headers["content-length"])
    reply_body = recv_exact(client, reply_length, already=reply_rest)
    print("客户端收到的响应头：")
    print(raw_reply_headers.decode("utf-8"))
    print(f"客户端收到的响应正文（{reply_length} 字节）：")
    print(reply_body.decode("utf-8"))

    client.close()
    conn.close()
    server.close()


def main() -> None:
    demo_get_request()
    print("=" * 60)
    demo_post_with_body()


# ===== 课后作业：手写 HTTP 请求解析和响应构造 =====
# 应用逻辑已经写好（TASKS 字典和 lookup_task / add_task），
# 你的任务是写出 HTTP 报文的"读请求 / 写响应"过程——对应本课 2、3 节。
# 两个终端分别运行：
#   终端 1：python network_lesson08.py server
#   终端 2：python network_lesson08.py client
# 协议约定：
#   GET  /tasks/1          -> 200 + {"id": 1, "content": "..."}
#   GET  /tasks/99         -> 404 + {"error": "not found"}
#   POST /tasks            -> 201 + 新建的任务（正文是 JSON {"content": "..."}）
#   其他路径               -> 404
#   非法 JSON / 缺 content -> 400 + {"error": "..."}


TASKS: dict[int, dict[str, object]] = {
    1: {"id": 1, "content": "买牛奶"},
    2: {"id": 2, "content": "跑步"},
}


def lookup_task(task_id: int) -> dict[str, object] | None:
    """现成的应用逻辑：按 id 查找任务，找不到返回 None。"""
    return TASKS.get(task_id)


def add_task(content: str) -> dict[str, object]:
    """现成的应用逻辑：追加一条任务并返回它。"""
    new_id = max(TASKS) + 1
    task = {"id": new_id, "content": content}
    TASKS[new_id] = task
    return task


def read_http_request(sock: socket.socket) -> tuple[str, str, dict[str, str], bytes]:
    """TODO 作业 1：从 socket 读出一条完整的 HTTP 请求。

    返回 (method, path, headers, body)。

    步骤：
    1. 用 recv_until(sock, b"\\r\\n\\r\\n") 读到头部结束（空行）。
       它返回 (头部字节, 空行之后已经多读到的字节)；
    2. 第一行是请求行，按空格拆成 method、path、version；
    3. 其余行按 "Name: Value" 拆成 headers 字典，键转成小写；
    4. 如果 headers 里有 content-length，用 recv_exact 收满那么多字节作为 body
       （already 参数传入步骤 1 多读到的部分）；没有 content-length 则 body 为 b""。
    任何一步对方提前关闭，让 recv_until / recv_exact 的 ConnectionError 向上传播即可。
    """
    # TODO 作业：完成这个函数（约 15 行，请复用上面的 recv_until / recv_exact）
    raise NotImplementedError


def write_http_response(
    sock: socket.socket,
    status: int,
    reason: str,
    body: bytes,
    content_type: str = "application/json; charset=utf-8",
) -> None:
    """TODO 作业 2：向 socket 写出一条完整的 HTTP 响应。

    布局：
      HTTP/1.1 {status} {reason}\\r\\n
      Content-Type: {content_type}\\r\\n
      Content-Length: {len(body)}\\r\\n
      Connection: close\\r\\n
      \\r\\n
      {body}

    用 sendall 一次发出。status 和 reason 由调用方决定（200 OK / 201 Created / 400 Bad Request / 404 Not Found）。
    """
    # TODO 作业：完成这个函数（约 8 行）
    raise NotImplementedError


def dispatch(method: str, path: str, body: bytes) -> tuple[int, str, bytes]:
    """现成的路由：根据方法和路径调用应用逻辑，返回 (status, reason, body)。不需要修改。"""
    if method == "GET" and path.startswith("/tasks/"):
        try:
            task_id = int(path.rsplit("/", 1)[-1])
        except ValueError:
            return 400, "Bad Request", json.dumps({"error": "id 必须是整数"}).encode("utf-8")
        task = lookup_task(task_id)
        if task is None:
            return 404, "Not Found", json.dumps({"error": "not found"}).encode("utf-8")
        return 200, "OK", json.dumps(task, ensure_ascii=False).encode("utf-8")

    if method == "POST" and path == "/tasks":
        try:
            data = json.loads(body.decode("utf-8"))
            content = data["content"]
            if not isinstance(content, str) or not content.strip():
                raise ValueError("content 不能为空")
        except (json.JSONDecodeError, KeyError, ValueError) as error:
            return 400, "Bad Request", json.dumps({"error": str(error)}).encode("utf-8")
        task = add_task(content.strip())
        return 201, "Created", json.dumps(task, ensure_ascii=False).encode("utf-8")

    return 404, "Not Found", json.dumps({"error": "not found"}).encode("utf-8")


def run_http_server() -> None:
    """服务器框架：完成 read_http_request / write_http_response 后即可运行。"""
    server = create_tcp_socket()
    server.bind(("127.0.0.1", HTTP_PORT))
    server.listen(5)
    print(f"HTTP 服务器在 127.0.0.1:{HTTP_PORT} 监听")
    try:
        while True:
            conn, addr = server.accept()
            print(f"来自 {addr} 的连接")
            try:
                method, path, _headers, body = read_http_request(conn)
                print(f"  {method} {path} 正文 {len(body)} 字节")
                status, reason, reply = dispatch(method, path, body)
                write_http_response(conn, status, reason, reply)
            except (ConnectionError, ValueError) as error:
                print(f"  读请求失败：{error}")
            finally:
                conn.close()
    except KeyboardInterrupt:
        print("服务器退出")
    finally:
        server.close()


def run_http_client() -> None:
    """客户端：用课程示例同款的手写报文，依次发四个请求检查作业。"""
    cases = [
        ("GET", "/tasks/1", b""),
        ("GET", "/tasks/99", b""),
        ("POST", "/tasks", json.dumps({"content": "读书"}).encode("utf-8")),
        ("GET", "/unknown", b""),
    ]
    for method, path, payload in cases:
        sock = create_tcp_socket()
        sock.settimeout(2.0)
        sock.connect(("127.0.0.1", HTTP_PORT))
        request = (
            f"{method} {path} HTTP/1.1\r\n"
            f"Host: 127.0.0.1\r\n"
            f"Content-Length: {len(payload)}\r\n"
            f"Content-Type: application/json\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode("ascii") + payload
        sock.sendall(request)
        reply = b""
        try:
            while True:
                chunk = sock.recv(1024)
                if not chunk:
                    break
                reply += chunk
        except TimeoutError:
            pass
        first_line = reply.split(b"\r\n", 1)[0].decode("ascii", errors="replace")
        print(f"{method} {path} -> {first_line}  ({len(reply)} 字节)")
        sock.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_http_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        run_http_client()
    else:
        main()
