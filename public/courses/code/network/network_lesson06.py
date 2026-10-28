"""第六课示例：TCP 可靠传输与粘包。"""

import socket
import sys
import time


def create_tcp_socket() -> socket.socket:
    """创建 IPv4 + TCP 的 socket。"""
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def start_server_and_client() -> tuple[socket.socket, socket.socket, socket.socket]:
    """在本机准备一对已连接的 socket，返回 (server, client, conn)。

    为了在单个进程里观察字节流行为，服务器和客户端交替执行；
    真实程序里它们是两个进程（第 5 课作业已经体会过）。
    """
    server = create_tcp_socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    client = create_tcp_socket()
    client.connect(("127.0.0.1", port))
    conn, _ = server.accept()
    return server, client, conn


def demo_sticky_and_split() -> None:
    """演示 TCP 字节流的两个现象：粘包（多条并成一次读到）和读不满（一条分多次读）。"""
    server, client, conn = start_server_and_client()

    # ---- 现象一：粘包。客户端连续发三条消息，中间不等确认 ----
    for text in ["第一条", "第二条", "第三条"]:
        client.sendall(text.encode("utf-8"))   # 三次 sendall 之间没有任何 recv
    time.sleep(0.05)                           # 稍等片刻，确保三段数据都已进入接收队列
    data = conn.recv(1024)                     # 服务器只 recv 一次
    print(f"服务器一次 recv 读到 {len(data)} 字节：{data!r}")
    print(f"  解码后看起来是：{data.decode('utf-8')}  ← 三条消息粘在一起，无法区分边界")

    # ---- 现象二：读不满。一条大消息，用小缓冲分多次读 ----
    big_message = "甲" * 60                    # 60 个汉字 = 180 字节（UTF-8 每字 3 字节）
    payload = big_message.encode("utf-8")
    client.sendall(payload)
    received = bytearray()
    rounds = 0
    while len(received) < len(payload):        # recv(n) 的 n 是上限，不是承诺；读满为止
        received += conn.recv(64)
        rounds += 1
    print(f"180 字节的消息用了 {rounds} 次 recv(64) 才拼完整（每次读到的都少于 64 字节的请求量）")

    client.close()
    conn.close()
    server.close()


# ===== 课程示例：分隔符协议 =====
# 解决粘包的思路之一：给每条消息加上边界标记（\n），接收方按标记切分。
# 关键点：缓冲区 buffer 必须跟着连接走——粘在一起的数据和拆开的数据都靠它拼回原样。

def send_line(sock: socket.socket, text: str) -> None:
    """按分隔符协议发送一条消息：内容 + 换行符。"""
    sock.sendall(text.encode("utf-8") + b"\n")


def recv_line(sock: socket.socket, buffer: bytearray, max_line: int = 4096) -> tuple[str, bytearray]:
    """按分隔符协议接收一条消息，返回（消息, 更新后的缓冲区）。

    buffer 保存"已经收到但还没凑成完整消息"的字节，必须由调用方保存并传回，
    因为一次 recv 可能粘着两条消息，也可能一条消息拆在多次 recv 里。
    收到空字节说明对方关闭，此时如果还有没拼完的数据，视为异常。
    """
    while True:
        index = buffer.find(b"\n")             # 缓冲区里已经有完整消息了吗？
        if index != -1:
            line = bytes(buffer[:index])
            del buffer[:index + 1]             # 从缓冲区移走这条消息（包括分隔符）
            return line.decode("utf-8"), buffer
        if len(buffer) > max_line:
            # 这里的max_line可以理解为，为了找一个line的最大字节缓存数，不是最大的行数
            raise ValueError("消息超过长度上限，疑似协议错误")
        chunk = sock.recv(1024)                # 缓冲区不够，继续读网络
        if not chunk:
            raise ConnectionError("对方已关闭连接，且没有剩余完整消息")
        buffer += chunk                        # 新读到的字节并入缓冲区，重新找 \n


def demo_line_protocol() -> None:
    """用分隔符协议收发三条消息：即使粘包、拆包，边界也不会乱。"""
    server, client, conn = start_server_and_client()

    # 客户端连发三条（中间不收），制造和 demo_sticky_and_split 相同的粘包条件
    for text in ["任务A", "任务B", "任务C"]:
        send_line(client, text)

    # 服务器用同一个 buffer 依次收三条：粘在一起也能正确切开
    buffer = bytearray()
    for _ in range(3):
        text, buffer = recv_line(conn, buffer)
        print(f"服务器收到一条消息：{text!r}")

    # 反方向再走一遍，确认双向可用
    for text in ("已收到任务A", "已收到任务B", "已收到任务C"):
        send_line(conn, text)
    for _ in range(3):
        text, buffer = recv_line(client, buffer)
        print(f"客户端收到回执：{text!r}")

    client.close()
    conn.close()
    server.close()


def main() -> None:
    demo_sticky_and_split()
    print()
    demo_line_protocol()


# ===== 课后作业：长度前缀协议的收发两端 =====
# 分隔符协议有个先天缺陷：消息内容里不能出现分隔符本身。
# 更常用的方案是"长度前缀"：每条消息前面加 4 字节，写明这条消息一共多少字节。
#   发送：[4 字节长度][消息内容]
#   接收：先收满 4 字节头部，解出长度 n，再精确收满 n 字节
# JSON 的 HTTP 接口（Content-Length）、二进制协议都用这个思路。
# 应用逻辑（回显服务）已经写好，你的任务是写出协议的收发两端。

FRAME_PORT = 9500


def run_frame_server() -> None:
    """服务器框架（协议函数完成后即可运行）：收到什么就回什么，收到 bye 结束。"""
    server = create_tcp_socket()
    server.bind(("127.0.0.1", FRAME_PORT))
    server.listen(1)
    print(f"长度前缀协议服务器在 127.0.0.1:{FRAME_PORT} 监听，等待连接……")

    conn, addr = server.accept()
    print(f"客户端 {addr} 已连接")
    while True:
        message = recv_frame(conn)
        if message == b"bye":
            break
        send_frame(conn, b"echo: " + message)
    print("客户端说再见了，服务器退出")
    conn.close()
    server.close()


def run_frame_client() -> None:
    """客户端框架（协议函数完成后即可运行）：依次发送三条消息并打印回显。"""
    client = create_tcp_socket()
    client.settimeout(2.0)
    client.connect(("127.0.0.1", FRAME_PORT))

    # 第二条很长（600 字节），会触发"一条消息拆成多次 recv"的路径
    texts = ["hello", "这条消息很长" * 75, "bye"]
    for text in texts:
        send_frame(client, text.encode("utf-8"))
        if text == "bye":
            break
        reply = recv_frame(client)
        print(f"请求 {text[:12]!r}… -> 响应 {reply[:40]!r}（{len(reply)} 字节）")

    print("客户端发送完毕")
    client.close()


def send_frame(sock: socket.socket, payload: bytes) -> None:
    """TODO 作业 1：按长度前缀协议发送一条消息。

    布局：前 4 字节是 payload 的长度（大端无符号整数），紧跟 payload 本体。
    提示：struct.pack(">I", len(payload)) 生成 4 字节头部；两次内容可以
    拼成一个 bytes 后一次 sendall。
    """
    # TODO 作业：完成这个函数（约 2 行）
    raise NotImplementedError


def recv_frame(sock: socket.socket) -> bytes:
    """TODO 作业 2：按长度前缀协议接收一条消息。

    步骤（对应课程 recv_line 的思路，但用"精确收满"代替"找分隔符"）：
    1. 循环调用 sock.recv，直到凑满 4 字节头部——recv(n) 是上限不是承诺；
    2. 用 struct.unpack(">I", header) 解出长度 n；
    3. 继续循环收满 n 字节，返回消息本体；
    4. 任何一步收到空字节 b''（对方关闭）都抛 ConnectionError。
    注意：recv 在循环里每次读到的字节数都可能少于预期，必须累加。
    """
    # TODO 作业：完成这个函数（约 15 行）
    raise NotImplementedError


if __name__ == "__main__":
    # 作业需要两个终端分别运行（同第 5 课）：
    #   终端 1：python network_lesson06.py server
    #   终端 2：python network_lesson06.py client
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_frame_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        run_frame_client()
    else:
        main()
