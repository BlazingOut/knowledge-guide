"""第一课示例：网络分层模型与协议栈。"""

# ===== 课程示例：模拟一次 HTTP 请求的逐层封装 =====
# 真实网络中，每一层都会在数据前面加上自己的控制信息（头部）。
# 这里用 b"层名|控制信息|数据" 的格式模拟这个过程，
# 目的是观察"发送端自上而下逐层加头、接收端自下而上逐层去头"的规律。
# 真实协议头是二进制字段，这里用可读文本代替，便于观察。

def add_http_header(payload: bytes, method: str, path: str) -> bytes:
    """应用层：把请求方法和路径作为 HTTP 的控制信息。

    输入 payload 是上层交给本层的数据；返回加了 HTTP 头的新字节串。
    """
    header = f"{method} {path} HTTP/1.1".encode("ascii")
    return b"HTTP|" + header + b"|" + payload


def add_tcp_header(data: bytes, src_port: int, dst_port: int) -> bytes:
    """传输层：TCP 头部记录两端端口，用于把数据交给主机上正确的进程。"""
    header = f"src={src_port},dst={dst_port}".encode("ascii")
    return b"TCP|" + header + b"|" + data


def add_ip_header(data: bytes, src_ip: str, dst_ip: str) -> bytes:
    """网络层：IP 头部记录两端 IP 地址，用于跨网络找到目标主机。"""
    header = f"src={src_ip},dst={dst_ip}".encode("ascii")
    return b"IP|" + header + b"|" + data


def add_ethernet_header(data: bytes, src_mac: str, dst_mac: str) -> bytes:
    """链路层：以太网帧头记录相邻设备的 MAC 地址。"""
    header = f"src={src_mac},dst={dst_mac}".encode("ascii")
    return b"ETH|" + header + b"|" + data


def build_frame(payload: bytes) -> bytes:
    """发送端封装：自上而下依次经过应用层、传输层、网络层、链路层。"""
    http_data = add_http_header(payload, "GET", "/api/tasks")
    tcp_data = add_tcp_header(http_data, src_port=53218, dst_port=8000)
    ip_data = add_ip_header(tcp_data, src_ip="192.168.1.8", dst_ip="203.0.113.20")
    frame = add_ethernet_header(ip_data, src_mac="a4:5e:60:11:22:33", dst_mac="3c:22:fb:aa:bb:cc")
    return frame


def parse_layer(frame: bytes, layer_name: bytes) -> tuple[dict[str, str], bytes]:
    """解封装的一步：剥掉一层头部，返回（解析出的字段, 剩余数据）。

    输入 frame 是当前剩余的字节数据，layer_name 是期望的最外层层名。
    格式必须是 b"层名|控制信息|剩余数据"。层名不符或缺少分隔符时抛出 ValueError。
    """
    parts = frame.split(b"|", 2)
    if len(parts) != 3 or parts[0] != layer_name:
        expected = layer_name.decode("ascii")
        raise ValueError(f"帧格式错误：期望 {expected} 层，实际开头是 {frame[:24]!r}")
    fields: dict[str, str] = {}
    for item in parts[1].split(b","):
        key, sep, value = item.partition(b"=")
        if not sep:
            raise ValueError(f"{expected} 层头部字段不完整：{parts[1]!r}")
        fields[key.decode("ascii")] = value.decode("ascii")
    return fields, parts[2]


def receive_frame(frame: bytes) -> None:
    """接收端解封装：自下而上逐层剥头，最后剩下应用层数据。"""
    fields, data = parse_layer(frame, b"ETH")
    print("链路层：剥掉 ETH 头，得到相邻设备", fields)

    fields, data = parse_layer(data, b"IP")
    print("网络层：剥掉 IP 头，得到两端地址", fields)

    fields, data = parse_layer(data, b"TCP")
    print("传输层：剥掉 TCP 头，按端口找到进程", fields)

    parts = data.split(b"|", 2)
    if len(parts) != 3 or parts[0] != b"HTTP":
        raise ValueError(f"应用层数据不符合 HTTP 格式：{data[:24]!r}")
    print("应用层：得到 HTTP 请求", parts[1].decode("ascii"), "负载", parts[2].decode("utf-8"))


def main() -> None:
    payload = '{"items": ["买牛奶"]}'.encode("utf-8")
    frame = build_frame(payload)
    print("发送端最终发出的字节串（头部是 ASCII，负载是 UTF-8）：")
    print(frame.decode("utf-8"))
    print()
    print("接收端逐层解封装：")
    receive_frame(frame)


# ===== 课后作业：解析收到的数据帧 =====
# 场景：你是一个待办事项服务的开发者，收到了客户端发来的两个字节串。
# 课程示例演示了"封装"（build_frame）和"边剥头边打印"（receive_frame），
# 作业要求反过来：写一个解析函数，把各层字段整理成一个字典返回。

def parse_frame(frame: bytes) -> dict[str, object]:
    """从链路层开始逐层解封装，返回各层关键字段。

    要求：
    1. 依次剥离 ETH、IP、TCP、HTTP 四层头部，可以复用或仿照 parse_layer；
    2. mac、ip、tcp 三层的控制信息解析成字典（键同课程示例）；
    3. HTTP 层要把 "METHOD PATH HTTP/1.1" 拆成 method 和 path 两个键，
       剩下的负载作为 body 键（bytes 类型即可，不要求解码）；
    4. 任何一层层名不符、缺少分隔符或头部字段不完整时，抛出 ValueError，
       消息中说明是哪一层出错；
    5. 返回的字典必须包含 mac、ip、tcp、method、path、body 六个键。
    """
    # TODO 作业：完成这个函数（约 15 行，尽量复用 parse_layer）
    raise NotImplementedError("请完成 parse_frame")


def homework() -> None:
    """完成 parse_frame 后，运行本文件观察两个样本帧的处理结果。"""
    # 样本一：用课程示例的封装函数构造的合法帧（客户端创建一条提醒）。
    body = '{"content": "买牛奶", "remind_at": "18:00"}'.encode("utf-8")
    http_data = add_http_header(body, "POST", "/api/reminders")
    tcp_data = add_tcp_header(http_data, src_port=53100, dst_port=8000)
    ip_data = add_ip_header(tcp_data, src_ip="192.168.1.15", dst_ip="192.168.1.8")
    valid_frame = add_ethernet_header(ip_data, src_mac="a4:5e:60:44:55:66", dst_mac="3c:22:fb:aa:bb:cc")

    # 样本二：传输中途被损坏的帧，TCP 层名被改成了 TC?。
    broken_frame = valid_frame.replace(b"TCP|", b"TC?", 1)

    samples = [("合法帧", valid_frame), ("损坏帧", broken_frame)]
    for name, frame in samples:
        print(f"--- {name} ---")
        print(frame.decode("ascii", errors="replace"))
        try:
            result = parse_frame(frame)
        except ValueError as error:
            print("解析失败：", error)
        else:
            print("解析结果：")
            for key, value in result.items():
                print(f"  {key} = {value}")
        print()


if __name__ == "__main__":
    main()
    # 完成 parse_frame 后，取消下一行注释再运行，检查作业结果。
    # homework()
