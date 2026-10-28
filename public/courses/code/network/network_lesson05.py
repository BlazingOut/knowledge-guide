"""第五课示例：socket 编程。"""

import socket
import sys


def create_tcp_socket() -> socket.socket:
    """创建 IPv4 + TCP 的 socket。AF_INET 表示 IPv4 地址族，SOCK_STREAM 表示 TCP。"""
    return socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def demo_udp_send_receive() -> None:
    """UDP：无连接，拿到地址直接发。服务器和客户端在本进程内顺序演示。

    注意：UDP 服务器和 TCP 服务器一样必须 bind 占住端口；
    "无连接"省掉的是握手和 accept，不是端口登记。
    """
    # UDP 服务器：必须 bind，让操作系统知道"发往这个端口的数据报放进这个 socket"。
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 端口填 0 不是"0 号端口"，而是约定：请系统从空闲端口里挑一个，
    # 挑好后用 getsockname() 查实际端口（真实项目里通常是配置指定的固定端口）。
    server.bind(("127.0.0.1", 0))
    server_addr = server.getsockname()
    print(f"UDP 服务器绑定在 {server_addr[0]}:{server_addr[1]}")

    # UDP 客户端：不用 connect（没有握手），也不用手写 bind——
    # 第一次 sendto 时内核自动分配一个临时端口（隐式绑定），
    # 所以服务器收到的 addr 里带着客户端的端口。
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client.sendto("你好，UDP".encode("utf-8"), server_addr)
    print("客户端：sendto 已发出（UDP 不建立连接、不等待确认）")

    data, addr = server.recvfrom(1024)        # 阻塞，直到有数据报到达；地址随包附带
    print(f"服务器：recvfrom 收到 {data.decode('utf-8')}，来自 {addr}")

    # 回应时直接 sendto 到来源地址，不需要 accept，也不存在"连接"。
    server.sendto("收到，UDP".encode("utf-8"), addr)
    print(f"客户端：recv 收到 {client.recv(1024).decode('utf-8')}")

    client.close()
    server.close()


def demo_tcp_exchange() -> None:
    """TCP：完整走一遍 socket 生命周期，包括一次连接内的多次收发。

    为了在单个进程里演示，服务器和客户端代码交替执行；
    真实程序里它们通常是两个进程，甚至两台机器。
    """
    # ---- 服务器侧：创建 -> bind -> listen ----
    server = create_tcp_socket()
    server.bind(("127.0.0.1", 0))             # 占住一个地址和端口
    server.listen(1)                          # 参数：等待被 accept 的连接排队上限
    port = server.getsockname()[1]
    print(f"TCP 服务器监听 127.0.0.1:{port}")

    # ---- 客户端侧：创建 -> connect ----
    client = create_tcp_socket()
    client.connect(("127.0.0.1", port))       # 阻塞，直到连接建立（握手由内核完成，第 4 课）
    print("客户端：connect 完成")

    # ---- 服务器侧：accept 取出一条已建立的连接 ----
    conn, addr = server.accept()              # 阻塞，直到有客户端连上
    print(f"服务器：accept 到 {addr}，conn 是与这个客户端一一对应的新 socket")

    # ---- 同一条连接内收发两轮：交替读写 ----
    for i in (1, 2):
        client.sendall(f"消息 {i}".encode("utf-8"))
        data = conn.recv(1024)                # 参数是"本次最多读多少字节"，不是"必须读满"
        print(f"服务器：第 {i} 次收到 {data.decode('utf-8')}")
        conn.sendall(f"已收到消息 {i}".encode("utf-8"))
        print(f"客户端：recv 收到 {client.recv(1024).decode('utf-8')}")

    # ---- 客户端关闭连接：服务器 recv 返回空字节 ----
    client.close()
    data = conn.recv(1024)
    if data == b"":
        print("服务器：recv 返回空字节 b''，说明对方已正常关闭连接")
    conn.close()
    server.close()


def demo_connection_refused() -> None:
    """连接一个没人监听的端口，观察 ConnectionRefusedError。"""
    dead = create_tcp_socket()
    try:
        dead.connect(("127.0.0.1", 1))        # 端口 1 上几乎不会有进程监听
    except ConnectionRefusedError as error:
        print(f"连接被拒绝：{error}")
        print("原因：目标地址和端口上没有进程监听，操作系统直接拒绝")
    finally:
        dead.close()


def main() -> None:
    demo_udp_send_receive()
    print()
    demo_tcp_exchange()
    print()
    demo_connection_refused()


# ===== 课后作业：UDP 求和服务的客户端与服务器 =====
# 应用逻辑已经写好（parse_sum_request），你的任务是写出"请求和响应的过程"——
# 也就是 4.2 节那 8 步对应的代码：服务器循环收发，客户端依次请求。
# 这次作业需要两个终端分别运行（和真实的服务器、客户端是两个进程一样）：
#   终端 1：python network_lesson05.py server   （先启动）
#   终端 2：python network_lesson05.py client   （后运行）
# 协议约定（UDP 数据报天然有边界，一条请求就是一个包）：
#   请求 "3,4"   -> 响应 "sum=7"
#   请求不合法   -> 响应 "error: ..."（必须包含关键字 error）
#   请求 "bye"   -> 不响应，服务结束

SERVER_PORT = 9400   # 固定端口：客户端必须能"找到"服务器，所以不能再用端口 0


def parse_sum_request(text: str) -> str:
    """现成的应用逻辑，不需要修改：把 "3,4" 变成 "sum=7"。

    逗号分隔两部分，各自去空白后必须是整数；不合法抛 ValueError。
    """
    left, sep, right = text.partition(",")
    if not sep or not left.strip() or not right.strip():
        raise ValueError("请求应为两个逗号分隔的整数，如 3,4")
    return f"sum={int(left.strip()) + int(right.strip())}"


def run_sum_server() -> None:
    """TODO 作业 1：UDP 服务器（对应流程的第 1、5、6 步）。

    1. 创建 SOCK_DGRAM socket，bind 到 ("127.0.0.1", SERVER_PORT)；
    2. 循环 recvfrom(1024) 等请求（和课程示例一样，阻塞等待）；
    3. 请求是 "bye" 时打印"服务结束"并结束函数；
    4. 其他请求调用 parse_sum_request 算响应；它抛出的 ValueError 要
       捕获并转换成 f"error: {错误信息}"，绝不能让服务崩溃；
    5. 把响应 sendto 回 recvfrom 返回的地址。
    完成后用 `python network_lesson05.py server` 运行本函数。
    """
    # TODO 作业：完成这个函数（约 12 行）
    raise NotImplementedError


def run_sum_client() -> None:
    """TODO 作业 2：UDP 客户端（对应流程的第 2、3、7 步）。

    1. 创建 SOCK_DGRAM socket，并 settimeout(2.0)——服务器没响应时
       recvfrom 会抛 TimeoutError 而不是永远卡住；
    2. 对 texts 里的每个请求：sendto 到 ("127.0.0.1", SERVER_PORT)，
       然后 recvfrom(1024) 收响应，打印"请求 xx -> 响应 xx"；
    3. 全部完成后发送 "bye"（不需要等响应）。
    必须先启动服务器再运行客户端，否则每次 recvfrom 都会超时。
    """
    texts = ["3,4", "10,-2", " 3 , 4 ", "3;4"]
    # TODO 作业：完成这个函数（约 10 行）
    raise NotImplementedError


if __name__ == "__main__":
    # 命令行带参数时运行作业（两个终端分别运行 server / client），
    # 不带参数时运行课程示例。
    if len(sys.argv) > 1 and sys.argv[1] == "server":
        run_sum_server()
    elif len(sys.argv) > 1 and sys.argv[1] == "client":
        run_sum_client()
    else:
        main()
