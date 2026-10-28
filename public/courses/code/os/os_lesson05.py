"""第五课：CPU 调度模拟。"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    name: str
    arrival: int
    burst: int
    priority: int = 0


@dataclass
class ScheduleResult:
    order: list[str]
    completion: dict[str, int]
    waiting: dict[str, int]
    turnaround: dict[str, int]

    @property
    def average_waiting(self) -> float:
        return sum(self.waiting.values()) / len(self.waiting)

    @property
    def average_turnaround(self) -> float:
        return sum(self.turnaround.values()) / len(self.turnaround)


def make_result(jobs: list[Job], completion: dict[str, int], order: list[str]) -> ScheduleResult:
    turnaround = {
        job.name: completion[job.name] - job.arrival
        for job in jobs
    }
    waiting = {
        job.name: turnaround[job.name] - job.burst
        for job in jobs
    }
    return ScheduleResult(order, completion, waiting, turnaround)


def fcfs(jobs: list[Job]) -> ScheduleResult:
    """先来先服务：非抢占式。"""
    current = 0
    completion: dict[str, int] = {}
    order: list[str] = []
    for job in sorted(jobs, key=lambda item: (item.arrival, item.name)):
        current = max(current, job.arrival)
        current += job.burst
        completion[job.name] = current
        order.append(job.name)
    return make_result(jobs, completion, order)


def sjf(jobs: list[Job]) -> ScheduleResult:
    """非抢占式最短作业优先。"""
    current = 0
    remaining = set(jobs)
    completion: dict[str, int] = {}
    order: list[str] = []
    while remaining:
        available = [job for job in remaining if job.arrival <= current]
        if not available:
            current = min(job.arrival for job in remaining)
            continue
        job = min(available, key=lambda item: (item.burst, item.arrival, item.name))
        remaining.remove(job)
        current += job.burst
        completion[job.name] = current
        order.append(job.name)
    return make_result(jobs, completion, order)


def round_robin(jobs: list[Job], quantum: int) -> ScheduleResult:
    """时间片轮转：抢占式，quantum 必须为正数。"""
    if quantum <= 0:
        raise ValueError("时间片必须大于 0")

    current = 0
    pending = sorted(jobs, key=lambda item: (item.arrival, item.name))
    durations = {job.name: job.burst for job in jobs}
    completion: dict[str, int] = {}
    order: list[str] = []
    ready: deque[Job] = deque()

    while len(completion) < len(jobs):
        while pending and pending[0].arrival <= current:
            ready.append(pending.pop(0))
        if not ready:
            current = pending[0].arrival
            continue
        job = ready.popleft()
        run_for = min(quantum, durations[job.name])
        current += run_for
        durations[job.name] -= run_for
        if not order or order[-1] != job.name:
            order.append(job.name)
        while pending and pending[0].arrival <= current:
            ready.append(pending.pop(0))
        if durations[job.name]:
            ready.append(job)
        else:
            completion[job.name] = current
    return make_result(jobs, completion, order)


def print_result(name: str, result: ScheduleResult) -> None:
    print(f"{name}: 执行顺序 {' -> '.join(result.order)}")
    print(f"  平均等待时间: {result.average_waiting:.2f}")
    print(f"  平均周转时间: {result.average_turnaround:.2f}")


def demo() -> None:
    jobs = [
        Job("A", arrival=0, burst=8),
        Job("B", arrival=1, burst=4),
        Job("C", arrival=2, burst=2),
        Job("D", arrival=3, burst=1),
    ]
    print_result("FCFS", fcfs(jobs))
    print_result("SJF", sjf(jobs))
    print_result("RR(q=2)", round_robin(jobs, quantum=2))


def simulate_fcfs(jobs: list[Job]) -> ScheduleResult:
    """作业骨架：实现 FCFS。"""
    raise NotImplementedError("请实现 FCFS")


def simulate_round_robin(jobs: list[Job], quantum: int) -> ScheduleResult:
    """作业骨架：实现时间片轮转。"""
    raise NotImplementedError("请实现 Round Robin")


def compare_algorithms(jobs: list[Job]) -> dict[str, float]:
    """作业骨架：返回各算法的平均等待时间。"""
    raise NotImplementedError("请返回 FCFS、SJF、RR 的平均等待时间")


def homework() -> None:
    jobs = [
        Job("A", 0, 5),
        Job("B", 1, 3),
        Job("C", 2, 1),
    ]
    fcfs_result = simulate_fcfs(jobs)
    rr_result = simulate_round_robin(jobs, 2)
    comparison = compare_algorithms(jobs)
    assert fcfs_result.completion["A"] == 5
    assert rr_result.completion["A"] > 0
    assert set(comparison) == {"FCFS", "SJF", "RR"}
    print("作业验收通过")


if __name__ == "__main__":
    demo()
    # homework() 需要完成作业后手动取消注释。
