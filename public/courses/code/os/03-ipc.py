"""第三课：进程间通信（IPC）课程示例与作业。

只使用 Python 标准库。Windows 使用 spawn 启动子进程，因此所有入口
都放在 main() 和 if __name__ == "__main__" 保护下。
"""

from __future__ import annotations

import multiprocessing as mp
import os
import signal
import time
from typing import Any


def pipe_worker(read_fd: int, write_fd: int) -> None:
    """子进程从匿名管道读取父进程发送的字节。"""
    os.close(write_fd)
    message = os.read(read_fd, 1024)
    print(f"[pipe 子进程 pid={os.getpid()}] 收到: {message.decode()}")
    os.close(read_fd)


def pipe_connection_worker(connection: Any) -> None:
    """Windows spawn 模式下通过可传递的 Connection 接收消息。"""
    print(f"[Pipe 子进程 pid={os.getpid()}] 收到: {connection.recv()}")
    connection.close()


def demo_pipe() -> None:
    """演示父子进程传值；Windows 使用可传递的 Pipe 连接。"""
    if os.name == "nt":
        parent_connection, child_connection = mp.Pipe(duplex=False)
        process = mp.Process(
            target=pipe_connection_worker,
            args=(child_connection,),
        )
        process.start()
        child_connection.close()
        parent_connection.send("来自父进程的任务消息")
        parent_connection.close()
        process.join()
        return

    read_fd, write_fd = os.pipe()
    process = mp.Process(target=pipe_worker, args=(read_fd, write_fd))
    process.start()

    os.close(read_fd)
    message = "来自父进程的任务消息"
    os.write(write_fd, message.encode())
    os.close(write_fd)
    process.join()


def queue_worker(queue: mp.Queue[Any], worker_id: int) -> None:
    """子进程把结构化结果放入消息队列。"""
    result = {
        "worker_id": worker_id,
        "pid": os.getpid(),
        "message": f"worker-{worker_id} 已完成",
    }
    queue.put(result)


def demo_queue() -> None:
    """演示 multiprocessing.Queue 的复制传值。"""
    queue: mp.Queue[Any] = mp.Queue()
    processes = [
        mp.Process(target=queue_worker, args=(queue, worker_id))
        for worker_id in range(2)
    ]
    for process in processes:
        process.start()
    results = [queue.get() for _ in processes]
    for process in processes:
        process.join()

    print("[Queue 主进程] 收到结果:")
    for result in sorted(results, key=lambda item: item["worker_id"]):
        print(f"  {result}")


def value_worker(counter: mp.Value, amount: int) -> None:
    """直接修改父子进程共同映射的 Value。"""
    for _ in range(amount):
        with counter.get_lock():
            counter.value += 1


def demo_shared_value() -> None:
    """演示 Value 的共享内存语义，并用自带锁保护读改写。"""
    counter = mp.Value("i", 0)
    processes = [
        mp.Process(target=value_worker, args=(counter, 1000))
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join()
    print(f"[Value 主进程] 共享计数 = {counter.value}")


def signal_worker() -> None:
    """等待信号，展示 SIGTERM 可被处理。"""
    def handle_term(signum: int, _frame: Any) -> None:
        print(f"[信号子进程 pid={os.getpid()}] 收到信号 {signum}，准备退出")
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, handle_term)
    print(f"[信号子进程] pid={os.getpid()}，等待 SIGTERM 或 Ctrl+C")
    while True:
        time.sleep(1)


def demo_signal() -> None:
    """启动一个等待信号的子进程；默认不自动终止它。"""
    process = mp.Process(target=signal_worker)
    process.start()
    print(
        f"[主进程] 信号示例 pid={process.pid}，"
        "请在另一个终端发送 SIGTERM；完成后结束该进程。"
    )
    try:
        process.join(timeout=5)
    finally:
        if process.is_alive():
            process.terminate()
            process.join()


def child_send_record(queue: mp.Queue[Any], worker_id: int) -> None:
    """作业：子进程通过 Queue 返回记录，不能修改父进程 list。"""
    queue.put({"pid": os.getpid(), "worker_id": worker_id})


def register_with_threads(n: int) -> list[dict[str, int]]:
    """作业骨架：线程共享一份 list，返回 n 条线程记录。"""
    raise NotImplementedError("请使用 threading 完成")


def register_with_processes(n: int) -> list[dict[str, int]]:
    """作业骨架：进程通过 Queue 返回记录，不能共享普通 list。"""
    raise NotImplementedError("请使用 multiprocessing.Queue 完成")


def count_unique_pids(records: list[dict[str, int]]) -> int:
    """作业：统计记录中不同 PID 的数量。"""
    return len({record["pid"] for record in records})


def homework() -> None:
    """运行作业验收。完成前两个函数后取消 main 中的注释。"""
    thread_records = register_with_threads(4)
    process_records = register_with_processes(4)
    assert len(thread_records) == 4
    assert len(process_records) == 4
    assert count_unique_pids(thread_records) == 1
    assert count_unique_pids(process_records) == 4
    print("作业验收通过")


def main() -> None:
    print("=== 1. 匿名管道：字节流传值 ===")
    demo_pipe()
    print("\n=== 2. 消息队列：复制传递结构化结果 ===")
    demo_queue()
    print("\n=== 3. 共享 Value：显式共享内存 ===")
    demo_shared_value()
    # demo_signal() 需要观察信号时手动取消注释。
    # homework() 需要完成作业函数后手动取消注释。


if __name__ == "__main__":
    mp.freeze_support()
    main()
