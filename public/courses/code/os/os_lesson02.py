"""第二课示例：进程与线程。"""

from __future__ import annotations

import os
import threading
import time
from multiprocessing import Process, Queue

PROCESS_N = 200_000
THREAD_N = 8_000


# ===== 课程示例：同一件计数，分别用进程和线程来做 =====
# 多进程改的是各自地址空间里的副本，父进程看不到；
# 多线程改的是同一份全局变量，但无保护的 += 会丢更新。


isolated_counter = 0
shared_counter = 0


def increment_in_process(times: int) -> None:
    """子进程里把模块级计数器加 times 次，然后打印自己的 pid 和结果。

    输入 times 是循环次数。无返回值。副作用：只修改本进程的 isolated_counter，
    并往标准输出打印一行。父进程的 isolated_counter 不会被改到。
    """
    global isolated_counter
    for _ in range(times):
        isolated_counter += 1
    print(f"子进程 pid={os.getpid()} 里的计数 = {isolated_counter}")


def increment_in_thread(times: int) -> None:
    """线程里把模块级计数器加 times 次。

    输入 times 是循环次数。无返回值。副作用：修改本进程共享的 shared_counter。
    这里把 += 拆成"读出 → 加一 → 写回"，并在中间 time.sleep(0) 主动让出 GIL，
    放大交错窗口。CPython 下紧凑的 shared_counter += 1 常常在一次 GIL 持有期内
    跑完，竞态不容易被观察到——拆开以后丢更新会稳定出现。
    """
    global shared_counter
    for _ in range(times):
        current = shared_counter
        current += 1
        time.sleep(0)
        shared_counter = current


def demo_processes() -> None:
    """启动两个子进程各加 N 次，观察父子、子子之间互不影响。"""
    global isolated_counter
    isolated_counter = 0
    print(f"父进程 pid={os.getpid()}，开始前 isolated_counter = {isolated_counter}")

    workers = [
        Process(target=increment_in_process, args=(PROCESS_N,)),
        Process(target=increment_in_process, args=(PROCESS_N,)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    print(f"两个子进程都结束后，父进程里的 isolated_counter = {isolated_counter}")
    print("  （仍是 0：子进程改的是自己的地址空间，写不回父亲）")


def demo_threads() -> None:
    """启动两条线程各加 N 次，观察共享同一份变量、以及无保护写入会丢更新。"""
    global shared_counter
    shared_counter = 0
    print(f"主线程 pid={os.getpid()} ident={threading.get_ident()}")
    print(f"开始前 shared_counter = {shared_counter}，期望最终值 = {2 * THREAD_N}")

    workers = [
        threading.Thread(target=increment_in_thread, args=(THREAD_N,)),
        threading.Thread(target=increment_in_thread, args=(THREAD_N,)),
    ]
    for worker in workers:
        worker.start()
        print(f"  已启动一条线程 ident={worker.ident}，仍在同一进程 pid={os.getpid()}")
    for worker in workers:
        worker.join()

    print(f"两条线程都结束后，shared_counter = {shared_counter}")
    if shared_counter < 2 * THREAD_N:
        print("  （小于 2N：两条线程在改同一份变量，读-改-写交错，有更新丢失）")
    else:
        print("  （这次碰巧等于 2N：交错没发生不代表没有竞态，再跑几次）")


def main() -> None:
    print("===== 多进程：各加各的 =====")
    demo_processes()
    print()
    print("===== 多线程：加的是同一份 =====")
    demo_threads()


# ===== 课后作业：任务登记 =====
# 课程示例用一个整数计数；作业改成每个 worker 登记一条记录，
# 主流程再汇总。进程那边禁止靠共享 list 传结果——那是线程才做得到的事。


def register_with_threads(n: int) -> list[dict[str, int]]:
    """启动 n 条线程，每条往同一份 list 追加一条登记记录，join 后返回这份 list。

    每条记录必须包含三个键：
    - pid: os.getpid()，所有记录应相同（线程共享进程）
    - ident: threading.get_ident()，所有记录应两两不同（线程独享 ident）
    - worker_id: 启动时传入的 0 到 n-1

    记录条数必须等于 n。不要在函数里打印。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 register_with_threads")


def register_with_processes(n: int) -> list[dict[str, int]]:
    """启动 n 个子进程，收集每条登记记录后返回。

    记录字段与 register_with_threads 相同。子进程不能通过修改父进程的
    普通 list 交差（地址空间隔离，append 写不回去），必须用函数返回值
    或 multiprocessing.Queue 把记录送回父进程。

    返回的 list 条数必须等于 n；所有记录的 pid 必须两两不同，且都与
    父进程的 PID 不同。不要在函数里打印。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 register_with_processes")


def count_unique_pids(records: list[dict[str, int]]) -> int:
    """返回记录里不同 PID 的个数。

    线程那份应返回 1，进程那份应返回 n。不要在函数里打印。
    """
    # TODO 作业：完成这个函数（约 1 行）
    raise NotImplementedError("请完成 count_unique_pids")


def homework() -> None:
    """完成三个函数后，取消 __main__ 里对本函数的注释再运行。"""
    n = 4
    thread_records = register_with_threads(n)
    assert len(thread_records) == n, f"线程登记条数应为 {n}，实际 {len(thread_records)}"
    thread_pids = {item["pid"] for item in thread_records}
    thread_idents = {item["ident"] for item in thread_records}
    assert thread_pids == {os.getpid()}, f"线程应共享父进程 PID，实际 {thread_pids}"
    assert len(thread_idents) == n, f"线程 ident 应两两不同，实际 {thread_idents}"
    assert count_unique_pids(thread_records) == 1

    process_records = register_with_processes(n)
    assert len(process_records) == n, f"进程登记条数应为 {n}，实际 {len(process_records)}"
    process_pids = {item["pid"] for item in process_records}
    assert os.getpid() not in process_pids, "子进程 PID 不应等于父进程"
    assert len(process_pids) == n, f"子进程 PID 应两两不同，实际 {process_pids}"
    assert count_unique_pids(process_records) == n

    print("作业检查通过：")
    print(f"  线程登记 {thread_records}")
    print(f"  进程登记 {process_records}")


if __name__ == "__main__":
    main()
    # 完成三个作业函数后，取消下一行注释再运行，检查作业结果。
    # homework()
