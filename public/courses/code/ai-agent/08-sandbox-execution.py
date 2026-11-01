"""第八课示例：进程级沙盒（超时强杀、输出防逃逸）与沙箱资源池调度。"""

from __future__ import annotations

import subprocess
import sys
import time
from dataclasses import dataclass, field


# ===== 课程示例：进程级沙盒 =====


def run_sandboxed(code: str, timeout_s: float = 2.0, max_output: int = 200) -> str:
    """在独立子进程里执行代码：超时强杀 + 输出边界 + 异常提炼。

    用 subprocess 而不是线程：进程可以被真正杀死——第三课的线程超时
    只是"不再等待"，这里的超时是"进程已经没了"。
    """
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.monotonic() - start
        return f"超时强杀：超过 {timeout_s} 秒，进程已被杀死（真实耗时 {elapsed:.1f}s）"
    if proc.returncode != 0:
        # 只提炼异常类型与最后一行，不回传完整堆栈：防内部路径泄露 + 上下文污染
        lines = [line for line in proc.stderr.strip().splitlines() if line.strip()]
        brief = lines[-1] if lines else "未知错误"
        return f"沙盒执行失败：{brief}"
    out = proc.stdout.strip()
    if len(out) > max_output:
        return (
            f"输出越界：{len(out)} 字符超过边界 {max_output}，"
            f"已截断：{out[:max_output]}…"
        )
    return out or "(无输出)"


# ===== 课程示例：沙箱资源池 =====


@dataclass
class SandboxSlot:
    id: int
    state: str  # "warm" / "busy" / "recycling"
    idle_s: float = 0.0


@dataclass
class PoolConfig:
    warm_size: int = 2        # 预热槽位：请求来之前容器已启动
    max_slots: int = 4        # 总槽位上限
    idle_ttl_s: float = 60.0  # 空闲多久销毁回收


class SandboxPool:
    """沙箱资源池：预热、复用、TTL 销毁、排队与超限拒绝（模拟调度）。"""

    def __init__(self, config: PoolConfig) -> None:
        self.config = config
        self.slots = [SandboxSlot(i, "warm") for i in range(config.warm_size)]
        self.queue: list[tuple[str, str]] = []  # (request_id, priority)
        self.log: list[str] = []

    def submit(self, request_id: str, priority: str) -> str:
        """调度决策：warm 槽直接分配；无槽未超上限则新建；超限按优先级处理。"""
        warm = [s for s in self.slots if s.state == "warm"]
        if warm:
            warm[0].state = "busy"
            self.log.append(f"{request_id}({priority}) -> 命中预热槽 #{warm[0].id}，启动延迟≈0")
            return f"命中预热槽 #{warm[0].id}"
        if len(self.slots) < self.config.max_slots:
            slot = SandboxSlot(len(self.slots), "busy")
            self.slots.append(slot)
            self.log.append(f"{request_id}({priority}) -> 新建槽 #{slot.id}（冷启动，有启动延迟）")
            return f"新建槽 #{slot.id}"
        if priority == "high":
            self.queue.append((request_id, priority))
            self.log.append(f"{request_id}({priority}) -> 排队等待（槽位全满）")
            return "排队等待"
        self.log.append(f"{request_id}({priority}) -> 超过上限，拒绝或降级")
        return "超过上限，拒绝（低优先级降级处理）"

    def recycle(self, slot_id: int) -> None:
        """执行完成后回收；空闲超过 TTL 销毁。"""
        slot = next(s for s in self.slots if s.id == slot_id)
        slot.state = "warm"
        slot.idle_s = 0.0
        self.log.append(f"槽 #{slot_id} 已回收为空闲")

    def tick_ttl(self) -> None:
        """模拟时间推进：空闲超 TTL 的槽位销毁，池子收缩。"""
        for slot in self.slots:
            if slot.state == "warm":
                slot.idle_s += 30.0
        expired = [s for s in self.slots if s.state == "warm" and s.idle_s >= self.config.idle_ttl_s]
        for slot in expired:
            slot.state = "recycling"
            self.log.append(f"槽 #{slot.id} 空闲超过 TTL，销毁回收（池子收缩）")


def main() -> None:
    print("路径 A：进程级沙盒——四项能力")
    print(
        "慢任务 ->",
        run_sandboxed("import time; time.sleep(5); print('done')", timeout_s=2.0),
    )
    print(
        "超长输出 ->",
        run_sandboxed("print('x' * 10000)", max_output=80),
    )
    print(
        "异常崩溃 ->",
        run_sandboxed("raise ValueError('数据库连接断开')"),
    )
    print(
        "正常执行 ->",
        run_sandboxed("print(\"查询结果：['周一慢跑']\")"),
    )
    print()

    print("路径 B：沙箱资源池调度")
    pool = SandboxPool(PoolConfig(warm_size=2, max_slots=3, idle_ttl_s=60.0))
    print(pool.submit("r1", "high"))     # 命中预热
    print(pool.submit("r2", "high"))     # 命中预热
    print(pool.submit("r3", "normal"))   # 新建（达到上限 3）
    print(pool.submit("r4", "high"))     # 槽位全满 -> 排队
    print(pool.submit("r5", "normal"))   # 槽位全满 -> 低优先级拒绝
    pool.recycle(0)
    print("回收槽 #0 后：", pool.submit("r6", "high"))  # 回到预热池，直接命中
    print("调度记录：")
    for line in pool.log:
        print("  ", line)

    print()
    print("路径 B2：空闲 TTL 销毁（预热槽不被使用，池子收缩）")
    pool2 = SandboxPool(PoolConfig(warm_size=1, max_slots=2, idle_ttl_s=60.0))
    pool2.tick_ttl()
    pool2.tick_ttl()  # 两次推进后空闲超过 TTL
    for line in pool2.log:
        print("  ", line)


# ===== 课后作业：资源池的调度决策与异常提炼 =====


def acquire(request_id: str, priority: str) -> str:
    """TODO 作业 1：按优先级返回调度决策文案。

    规则：warm 槽存在 -> "命中预热槽"；未达上限 -> "新建槽（冷启动）"；
    达到上限且 high -> "排队等待"；达到上限且 normal -> "拒绝（降级）"。
    返回文案即可，不要求真的操作池子。
    """
    raise NotImplementedError("请完成 acquire")


def summarize_traceback(stderr: str) -> str:
    """TODO 作业 2：从完整堆栈里提炼一句话错误。

    要求：只返回最后一行非空文本；行数超过 3 行时说明"（堆栈已提炼）"；
    绝不包含文件路径（防止泄露内部信息）。
    """
    raise NotImplementedError("请完成 summarize_traceback")


def homework() -> None:
    for rid, pri in [("s1", "high"), ("s2", "high"), ("s3", "normal"), ("s4", "high")]:
        print(rid, pri, "->", acquire(rid, pri))
    tb = (
        "Traceback (most recent call last):\n"
        "  File \"/srv/app/sandbox/worker.py\", line 9, in run\n"
        "    raise ValueError('笔记服务暂时不可用')\n"
        "ValueError: 笔记服务暂时不可用"
    )
    print("提炼结果：", summarize_traceback(tb))


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
