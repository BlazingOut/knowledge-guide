"""第六课示例：单 Agent 循环、规划+执行两角色与 Agentic Workflow 的对比。"""

from __future__ import annotations

from dataclasses import dataclass, field


# ===== 课程示例：三种形态的实现与统计 =====


@dataclass
class LifeStore:
    records: dict[str, list[str]] = field(default_factory=dict)
    plans: list[str] = field(default_factory=list)


@dataclass
class Stats:
    """一次运行的统计：模型决策次数、工具调用次数、失败是否恢复、最终计划。"""

    model_calls: int = 0
    tool_calls: int = 0
    recovered: bool = False
    plans: list[str] = field(default_factory=list)


def search_records(kind: str, fail: bool = False) -> str:
    if fail:
        return "查询失败：数据库连接断开"
    return f"查询结果：{STORE.records.get(kind, [])}"


def add_plan(title: str) -> str:
    STORE.plans.append(title)
    return f"已添加计划：{title}"


class SingleAgentLLM:
    """单 Agent 假模型：自己决定下一步，自己看到所有观察。"""

    def __init__(self) -> None:
        self.retried = False

    def decide(self, contents: str) -> tuple[str, dict]:
        """返回 (kind, payload)。kind 为 tool 或 final。"""
        if "查询失败" in contents and not self.retried:
            self.retried = True
            return "tool", {"name": "search_records", "args": {"kind": "health"}}
        if "查询失败" in contents:
            return "final", {"text": "查询失败两次，向用户说明。"}
        if "已添加计划" in contents:
            return "final", {"text": "已完成，计划已添加。"}
        if "查询结果" in contents:
            return "tool", {"name": "add_plan", "args": {"title": "今晚跑步"}}
        return "tool", {"name": "search_records", "args": {"kind": "health"}}


def run_single_agent(goal: str, max_steps: int = 6) -> tuple[str, Stats]:
    """路径 A：单 Agent 循环，失败时自己重试。"""
    stats = Stats()
    llm = SingleAgentLLM()
    searches = 0
    messages: list[dict[str, str]] = [
        {"role": "system", "content": "你是生活管家，按观察决定下一步。"},
        {"role": "user", "content": goal},
    ]
    for _ in range(max_steps):
        last = messages[-1]["content"]  # 只看最近一条观察，避免被旧失败消息干扰
        kind, payload = llm.decide(last)
        stats.model_calls += 1
        if kind == "final":
            return payload["text"], stats
        if payload["name"] == "search_records":
            searches += 1
            result = search_records("health", fail=(searches == 1))  # 第一次失败，重试成功
        else:
            result = add_plan(payload["args"]["title"])
            stats.plans.append(payload["args"]["title"])
        stats.tool_calls += 1
        if "查询失败" in result:
            stats.recovered = True  # 失败后模型重新决策
        messages.append({"role": "tool", "content": result})
    return "已达最大步数", stats


class PlannerLLM:
    """规划 Agent：只做决策、不碰工具；靠执行 Agent 的结果继续。"""

    def __init__(self) -> None:
        self.retried = False

    def plan(self, result: str = "") -> str:
        if "查询失败" in result and not self.retried:
            self.retried = True
            return "重查记录"
        if "查询失败" in result:
            return "放弃：查询两次失败，向用户说明"
        if "查询结果" in result:
            return "不足则加计划"
        return "先查记录；若不足则添加计划"


class ExecutorLLM:
    """执行 Agent：只执行计划的一步，把结果交回给规划 Agent。"""

    def __init__(self) -> None:
        self.searches = 0

    def execute(self, task: str) -> str:
        if "记录" in task or "重查" in task:
            self.searches += 1
            return search_records("health", fail=(self.searches == 1))  # 第一次失败，重试成功
        return search_records("health")


def run_orchestrator(goal: str) -> tuple[str, Stats]:
    """路径 B：规划 Agent + 执行 Agent 两角色，同样的失败要走两个角色的往返。"""
    stats = Stats()
    planner, executor = PlannerLLM(), ExecutorLLM()

    stats.model_calls += 1
    task = planner.plan()
    stats.model_calls += 1
    result = executor.execute(task)
    stats.tool_calls += 1
    if "查询失败" in result:
        stats.recovered = True
        stats.model_calls += 1
        task = planner.plan(result)
        stats.model_calls += 1
        result = executor.execute(task)
        stats.tool_calls += 1
    if "查询失败" in result:
        return "查询失败两次，任务终止。", stats

    stats.model_calls += 1
    decision = planner.plan(result)  # "不足则加计划"
    if "不足" in decision and "['周一慢跑']" in result:
        add_plan("今晚跑步")
        stats.tool_calls += 1
        stats.plans.append("今晚跑步")
    return "已完成：查记录并添加计划。", stats


class ModelJudge:
    """Agentic Workflow 里唯一交给模型的判断：记录够不够。"""

    def is_enough(self, result: str) -> bool:
        return "['周一慢跑', '周三游泳']" in result or len(result) > 40


def run_workflow(goal: str) -> tuple[str, Stats]:
    """路径 C：主路径固定代码，只有"是否足够"这一处交给模型。"""
    stats = Stats()
    result = search_records("health")
    stats.tool_calls += 1
    stats.model_calls += 1  # 唯一一次模型决策
    if not ModelJudge().is_enough(result):
        add_plan("今晚跑步")
        stats.tool_calls += 1
        stats.plans.append("今晚跑步")
    return "已完成。", stats


def main() -> None:
    global STORE

    STORE = LifeStore(records={"health": ["周一慢跑"]})
    print("路径 A：单 Agent 循环——失败自己看到、自己重试")
    reply, stats_a = run_single_agent("先查运动记录，不足则加今晚跑步")
    print("结果：", reply, "| 模型决策", stats_a.model_calls, "次，工具", stats_a.tool_calls, "次，失败恢复", stats_a.recovered)
    print("最终计划：", stats_a.plans)
    print()

    STORE = LifeStore(records={"health": ["周一慢跑"]})
    print("路径 B：规划 + 执行 两角色——同样的失败要跨角色往返")
    reply, stats_b = run_orchestrator("先查运动记录，不足则加今晚跑步")
    print("结果：", reply, "| 模型决策", stats_b.model_calls, "次，工具", stats_b.tool_calls, "次，失败恢复", stats_b.recovered)
    print("最终计划：", stats_b.plans)
    print()

    STORE = LifeStore(records={"health": ["周一慢跑"]})
    print("路径 C：Agentic Workflow——主路径固定，局部交给模型")
    reply, stats_c = run_workflow("先查运动记录，不足则加今晚跑步")
    print("结果：", reply, "| 模型决策", stats_c.model_calls, "次，工具", stats_c.tool_calls, "次")
    print("最终计划：", stats_c.plans)
    print()

    print("对比：模型决策次数  A:", stats_a.model_calls, " B:", stats_b.model_calls, " C:", stats_c.model_calls)
    print("对比：工具调用次数  A:", stats_a.tool_calls, " B:", stats_b.tool_calls, " C:", stats_c.tool_calls)
    print()

    print("路径 D：错误被下一个 Agent 当成事实")
    STORE = LifeStore(records={"health": ["周一慢跑"]})
    executor_result = "查询结果：['周一慢跑','周二瑜伽','周三游泳','周四跳绳','周五骑行']"  # 错误但可信
    planner_decision = "记录已满 5 次，无需添加计划"
    print("执行 Agent 返回：", executor_result)
    print("规划 Agent 采信：", planner_decision, "（没有核实渠道，把执行结果当成事实）")
    print("真实记录：", STORE.records["health"], "，计划列表：", STORE.plans, "——任务静默做错了")


# ===== 课后作业：pipeline 的失败中断 =====

STUDY_PLANS: list[str] = []


def outline_agent(goal: str) -> str:
    return "复习提纲：1. 间隔重复 2. 艾宾浩斯曲线"  # 缺了费曼技巧


def review_agent(outline: str) -> str:
    if "费曼技巧" not in outline:
        return "需要重做：提纲缺少费曼技巧"
    return f"审查通过：{outline}"


def save_agent(outline: str) -> str:
    STUDY_PLANS.append(outline)
    return f"已保存：{outline}"


def run_pipeline(goal: str, stages: list[object]) -> str:
    """TODO 作业：依次调用 stages，统计并打印调用次数。

    中断规则：某一步返回以"需要重做"开头时，立即中断，
    返回该步输出，不再传给下一步（失败不继续向下游传播）。
    """
    raise NotImplementedError("请完成 run_pipeline")


def homework() -> None:
    stages = [outline_agent, review_agent, save_agent]
    result = run_pipeline("生成复习提纲", stages)
    print("pipeline 结果：", result)
    print("保存列表（应仍为空，说明失败没有继续传播到 save_agent）：", STUDY_PLANS)


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
