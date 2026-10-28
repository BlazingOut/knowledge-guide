"""第九课示例：崩溃恢复、超时重试熔断降级、行为漂移与人工审批流。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


# ===== 课程示例：幂等与崩溃恢复 =====


@dataclass
class LifeStore:
    plans: list[str] = field(default_factory=list)


STORE = LifeStore()
_PROCESSED: dict[str, str] = {}  # request_id -> title


def add_plan(title: str, request_id: str) -> str:
    if request_id in _PROCESSED:
        return f"重复请求（{request_id}），不重复执行；已有计划：{_PROCESSED[request_id]}"
    _PROCESSED[request_id] = title
    STORE.plans.append(title)
    return f"已添加计划：{title}（请求号 {request_id}）"


def run_agent_task(
    thread_id: str,
    steps: list[tuple[str, dict[str, str]]],
    checkpoint: dict,
    crash_after: int = 2,
) -> list[str]:
    """带 checkpoint 的执行：崩溃后同一 thread_id 续跑，已完成步骤不重放副作用。

    crash_after=N：执行到第 N 步后、写入 checkpoint 前模拟崩溃。
    """
    done = checkpoint.setdefault(thread_id, [])
    trace: list[str] = []
    for index, (tool, args) in enumerate(steps, 1):
        req_id = args.get("request_id")
        if req_id in done:
            trace.append(f"第 {index} 步 {tool}：已在 checkpoint，跳过（不重放副作用）")
            continue
        result = add_plan(args["title"], req_id)  # 先执行：副作用发生
        if "重复请求" in result:
            trace.append(f"第 {index} 步 {tool}：{result}（幂等兜底，副作用未重放）")
        else:
            trace.append(f"第 {index} 步 {tool}：{result}")
        if index == crash_after and "crashed" not in checkpoint:
            checkpoint["crashed"] = True
            raise RuntimeError("进程在写库后、落 checkpoint 前崩溃")
        done.append(req_id)
    return trace


# ===== 课程示例：重试、退避、熔断、降级 =====


class CircuitBreaker:
    """熔断器：连续失败达到阈值后打开，冷却期内的请求直接降级。"""

    def __init__(self, fail_threshold: int = 3, cooldown_s: float = 0.2) -> None:
        self.fail_threshold = fail_threshold
        self.cooldown_s = cooldown_s
        self.failures = 0
        self.open_until = 0.0

    def allow(self) -> bool:
        return time.monotonic() >= self.open_until

    def record_failure(self) -> None:
        self.failures += 1
        if self.failures >= self.fail_threshold:
            self.open_until = time.monotonic() + self.cooldown_s
            self.failures = 0

    def record_success(self) -> None:
        self.failures = 0


def unreliable_search(attempt: int) -> str | None:
    return None  # 每次都失败，用来演示熔断与降级


def call_with_retry_and_circuit(
    func: object,
    retries: int = 3,
    backoff_s: float = 0.02,
    breaker: CircuitBreaker | None = None,
) -> str:
    """带退避的重试 + 熔断：连续失败打开熔断，冷却期内直接降级。"""
    for attempt in range(1, retries + 1):
        if breaker is not None and not breaker.allow():
            return "熔断打开（冷却中）-> 降级：直接返回缓存结果"
        print(f"  第 {attempt} 次尝试…")
        result = func(attempt)
        if result is not None:
            if breaker is not None:
                breaker.record_success()
            return result
        if breaker is not None:
            breaker.record_failure()
        if attempt < retries:
            wait = backoff_s * attempt
            print(f"  失败，退避 {wait:.2f}s 后重试")
            time.sleep(wait)
    return "重试耗尽 -> 降级：返回缓存结果"


# ===== 课程示例：行为漂移检测 =====

GOAL = "查看运动记录，不足 2 次则添加跑步计划"  # goal 固定在系统指令/状态里，不靠模型记住


def check_action(action: str, seen: list[str]) -> list[str]:
    """漂移检测 + 重复动作检测：返回警告列表。"""
    warnings: list[str] = []
    if "运动" not in action and "跑步" not in action and "记录" not in action:
        warnings.append(f"漂移警告：动作「{action}」偏离目标「{GOAL}」")
    if action in seen:
        warnings.append(f"重复警告：动作「{action}」已执行过（死循环防护）")
    seen.append(action)
    return warnings


# ===== 课程示例：人工审批流 =====


@dataclass
class ApprovalRequest:
    id: str
    operation: str
    can_rollback: bool
    ttl_s: float
    created: float
    status: str = "pending"


class ApprovalQueue:
    """审批队列：挂起、审批、超时策略、结果回写。"""

    def __init__(self) -> None:
        self.items: list[ApprovalRequest] = []
        self.decisions: list[str] = []
        self._seq = 0

    def request(self, operation: str, ttl_s: float, can_rollback: bool, expired: bool = False) -> str:
        self._seq += 1
        created = time.monotonic() - ttl_s - 0.01 if expired else time.monotonic()
        self.items.append(ApprovalRequest(f"apr-{self._seq}", operation, can_rollback, ttl_s, created))
        return f"apr-{self._seq}"

    def approve(self, req_id: str) -> str:
        req = next(r for r in self.items if r.id == req_id)
        req.status = "approved"
        observation = f"审批通过：{req.operation} 已执行，结果写回 Observation"
        self.decisions.append(observation)
        return observation

    def reject(self, req_id: str) -> str:
        req = next(r for r in self.items if r.id == req_id)
        req.status = "rejected"
        observation = f"审批拒绝：{req.operation} 未执行，模型应向用户说明原因"
        self.decisions.append(observation)
        return observation

    def expire(self) -> list[str]:
        """超时处理：能自动回滚的操作自动通过，否则自动拒绝（失败代价不对称）。"""
        result: list[str] = []
        for req in self.items:
            if req.status != "pending":
                continue
            if time.monotonic() - req.created < req.ttl_s:
                continue
            if req.can_rollback:
                req.status = "approved"
                text = f"超时自动通过：{req.operation}（可回滚，失败代价低）"
            else:
                req.status = "timeout"
                text = f"超时自动拒绝：{req.operation}（不可回滚，失败代价高）"
            self.decisions.append(text)
            result.append(text)
        return result


def main() -> None:
    print("路径 A：崩溃恢复——同一 thread_id 从 checkpoint 续跑")
    steps = [
        ("add_plan", {"title": "今晚跑步", "request_id": "req-01"}),
        ("add_plan", {"title": "周三游泳", "request_id": "req-02"}),
        ("add_plan", {"title": "周六骑行", "request_id": "req-03"}),
    ]
    checkpoint: dict = {}
    try:
        run_agent_task("thread-1", steps, checkpoint, crash_after=2)
    except RuntimeError as exc:
        print("第一次执行崩溃：", exc)
    print("重启后续跑：")
    for line in run_agent_task("thread-1", steps, checkpoint):
        print("  ", line)
    print("最终计划：", STORE.plans, "（req-02 未重复写入，幂等兜底）")
    print()

    print("路径 B：重试 + 退避 + 熔断 + 降级")
    breaker = CircuitBreaker(fail_threshold=3, cooldown_s=0.2)
    print("第一次调用：")
    print("  ", call_with_retry_and_circuit(unreliable_search, breaker=breaker))
    print("冷却期内的下一次请求：")
    print("  ", call_with_retry_and_circuit(unreliable_search, breaker=breaker))
    print()

    print("路径 C：行为漂移与重复动作检测")
    seen: list[str] = []
    for action in ["search_records", "search_records", "send_advertisement"]:
        for warning in check_action(action, seen):
            print("  ", warning)
    print()

    print("路径 D：人工审批流")
    queue = ApprovalQueue()
    req_delete = queue.request("delete_records", ttl_s=5.0, can_rollback=False)
    req_restore = queue.request("restore_records", ttl_s=5.0, can_rollback=True, expired=True)
    req_spend = queue.request("add_expense_5000", ttl_s=5.0, can_rollback=False)
    print(f"挂起：{req_delete} / {req_restore} / {req_spend}")
    print("人工审批 add_expense：", queue.approve(req_spend))
    print("超时处理：")
    for decision in queue.expire():
        print("  ", decision)
    print("拒绝后回写：", queue.reject(req_delete))


# ===== 课后作业：崩溃恢复与审批超时决策 =====

STUDY_PLANS: list[str] = []


def resume_from_checkpoint(
    thread_id: str,
    steps: list[tuple[str, dict[str, str]]],
    checkpoint: dict,
) -> list[str]:
    """TODO 作业 1：崩溃恢复。要求见课程文档第 10 节。

    规则：checkpoint 里已记录的 request_id 跳过（标注"由幂等兜底，不重放"）；
    未记录的执行（调用 STUDY_ADD 写 STUDY_PLANS），并把 request_id 记入 checkpoint。
    不模拟崩溃，直接返回 trace 列表。
    """
    raise NotImplementedError("请完成 resume_from_checkpoint")


def decide_approval(can_rollback: bool, ttl_s: float, elapsed_s: float) -> str:
    """TODO 作业 2：审批超时决策。

    规则：未超时返回"仍在等待人工审批"；已超时且可回滚 -> "自动通过（可回滚）"；
    已超时且不可回滚 -> "自动拒绝（不可回滚，失败代价高）"。
    """
    raise NotImplementedError("请完成 decide_approval")


def study_add(title: str, request_id: str) -> str:
    if request_id in _PROCESSED:
        return f"重复请求（{request_id}）"
    _PROCESSED[request_id] = title
    STUDY_PLANS.append(title)
    return f"已加入复习：{title}"


def homework() -> None:
    steps = [
        ("study_add", {"title": "间隔重复 20 分钟", "request_id": "s-01"}),
        ("study_add", {"title": "费曼技巧 15 分钟", "request_id": "s-02"}),
        ("study_add", {"title": "卡片法 10 分钟", "request_id": "s-03"}),
    ]
    checkpoint: dict = {"th-1": ["s-01", "s-02"]}  # 前两步已执行过（含副作用），模拟崩溃前
    for line in resume_from_checkpoint("th-1", steps, checkpoint):
        print("  ", line)
    print("复习列表（应只有 s-03 是新加的）：", STUDY_PLANS)
    print("超时决策：", decide_approval(False, 5.0, 6.0))
    print("超时决策：", decide_approval(True, 5.0, 6.0))


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
