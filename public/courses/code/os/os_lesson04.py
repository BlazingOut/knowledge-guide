"""第四课：线程同步：竞态、锁与死锁。"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass


def unsafe_increment(times: int) -> int:
    """故意制造读-改-写竞态。"""
    counter = 0

    def worker() -> None:
        nonlocal counter
        for _ in range(times):
            current = counter
            time.sleep(0)
            counter = current + 1

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return counter


def safe_increment(times: int) -> int:
    """用互斥锁保护完整的读-改-写过程。"""
    counter = 0
    lock = threading.Lock()

    def worker() -> None:
        nonlocal counter
        for _ in range(times):
            with lock:
                counter += 1

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return counter


def deadlock_worker(
    first: threading.Lock,
    second: threading.Lock,
    ready: threading.Barrier,
) -> None:
    """按相反顺序获取两把锁，故意形成死锁。"""
    with first:
        ready.wait()
        with second:
            pass


def demonstrate_deadlock() -> bool:
    """复现死锁；返回两个线程是否在超时后仍未退出。"""
    lock_a = threading.Lock()
    lock_b = threading.Lock()
    ready = threading.Barrier(2)
    thread_a = threading.Thread(
        target=deadlock_worker,
        args=(lock_a, lock_b, ready),
        daemon=True,
    )
    thread_b = threading.Thread(
        target=deadlock_worker,
        args=(lock_b, lock_a, ready),
        daemon=True,
    )
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=0.5)
    thread_b.join(timeout=0.5)
    return thread_a.is_alive() and thread_b.is_alive()


def ordered_worker(
    lock_a: threading.Lock,
    lock_b: threading.Lock,
    counter: list[int],
) -> None:
    """所有线程按同一顺序加锁，避免循环等待。"""
    with lock_a:
        with lock_b:
            counter[0] += 1


def demonstrate_ordered_locks() -> int:
    lock_a = threading.Lock()
    lock_b = threading.Lock()
    counter = [0]
    threads = [
        threading.Thread(target=ordered_worker, args=(lock_a, lock_b, counter))
        for _ in range(4)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return counter[0]


@dataclass
class Product:
    producer_id: int
    sequence: int


def producer(
    buffer: queue.Queue[Product],
    producer_id: int,
    count: int,
) -> None:
    for sequence in range(count):
        buffer.put(Product(producer_id, sequence))
    print(f"生产者 {producer_id} 完成")


def consumer(
    buffer: queue.Queue[Product],
    result: list[Product],
    result_lock: threading.Lock,
) -> None:
    while True:
        item = buffer.get()
        try:
            if item is None:
                return
            with result_lock:
                result.append(item)
        finally:
            buffer.task_done()


def demo_producer_consumer() -> int:
    """用有界 Queue 实现生产者-消费者。"""
    buffer: queue.Queue[Product] = queue.Queue(maxsize=3)
    result: list[Product] = []
    result_lock = threading.Lock()
    consumers = [
        threading.Thread(
            target=consumer,
            args=(buffer, result, result_lock),
        )
        for _ in range(2)
    ]
    producers = [
        threading.Thread(target=producer, args=(buffer, producer_id, 5))
        for producer_id in range(2)
    ]
    for thread in consumers + producers:
        thread.start()
    for thread in producers:
        thread.join()
    for _ in consumers:
        buffer.put(None)
    buffer.join()
    for thread in consumers:
        thread.join()
    return len(result)


def homework_race_counter(times: int) -> int:
    """作业骨架：复现无锁计数问题。"""
    raise NotImplementedError("请实现无锁版本")


def homework_locked_counter(times: int) -> int:
    """作业骨架：用 Lock 修复计数问题。"""
    raise NotImplementedError("请实现加锁版本")


def homework_ordered_transfer() -> bool:
    """作业骨架：按固定顺序获取两把锁并完成转账。"""
    raise NotImplementedError("请实现固定加锁顺序")


def homework() -> None:
    """完成三个作业函数后取消 main 中的注释。"""
    assert homework_race_counter(1000) < 2000
    assert homework_locked_counter(1000) == 2000
    assert homework_ordered_transfer() is True
    print("作业验收通过")


def main() -> None:
    print("=== 1. 竞态与锁 ===")
    print(f"无锁结果: {unsafe_increment(1000)} / 2000")
    print(f"加锁结果: {safe_increment(1000)} / 2000")
    print("\n=== 2. 死锁 ===")
    print(f"是否观察到死锁: {demonstrate_deadlock()}")
    print(f"固定顺序完成次数: {demonstrate_ordered_locks()}")
    print("\n=== 3. 生产者-消费者 ===")
    print(f"消费总数: {demo_producer_consumer()}")
    # homework() 需要完成作业后手动取消注释。


if __name__ == "__main__":
    main()
