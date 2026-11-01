"""第四课示例：短期记忆窗口、长期记忆库、召回注入与污染控制。"""

from __future__ import annotations

from dataclasses import dataclass, field


# ===== 课程示例：短期窗口与长期记忆库 =====


@dataclass
class MemoryEntry:
    """一条长期记忆。来源、置信度、是否审核决定它可不可信。"""

    key: str
    fact: str
    source: str          # "user" / "model_inference" / "tool_observation"
    confidence: float    # 0~1
    reviewed: bool = False


class LongTermMemory:
    """跨会话的长期记忆：可写入、可召回、可回滚，写入有门槛。"""

    AUTO_THRESHOLD = 0.7  # 自动写入的置信度门槛

    def __init__(self) -> None:
        self.entries: dict[str, MemoryEntry] = {}

    def remember(self, entry: MemoryEntry) -> str:
        """按规则写入。

        - 同 key 已有不同事实 -> 冲突，进待审核，不直接覆盖；
        - user 来源，或置信度 >= 门槛且已审核 -> 写入；
        - 其余 -> 拒绝自动写入，需要人工确认。
        """
        old = self.entries.get(entry.key)
        if old is not None and old.fact != entry.fact:
            return (
                f"冲突：{entry.key} 已有“{old.fact}”（来源 {old.source}），"
                f"新事实“{entry.fact}”进待审核队列，未直接覆盖"
            )
        if entry.source == "user" or (
            entry.confidence >= self.AUTO_THRESHOLD and entry.reviewed
        ):
            self.entries[entry.key] = entry
            return f"已写入：{entry.key} = {entry.fact}"
        return (
            f"拒绝自动写入：{entry.key}（来源 {entry.source}，置信度 {entry.confidence}）"
            "——低于阈值或未经审核，需要人工确认"
        )

    def recall(self, keyword: str) -> list[MemoryEntry]:
        """按关键词召回：事实或 key 里包含关键词的条目。"""
        return [
            e for e in self.entries.values()
            if keyword in e.fact or keyword in e.key
        ]

    def revoke(self, key: str) -> str:
        """回滚一条记忆（污染时用来纠正）。"""
        if key in self.entries:
            del self.entries[key]
            return f"已回滚：{key}"
        return f"不存在：{key}"


class SessionBuffer:
    """短期记忆：会话消息的窗口。超过上限时把最老的若干条折叠成一条摘要。"""

    def __init__(self, max_messages: int = 8) -> None:
        self.max_messages = max_messages
        self.messages: list[dict[str, str]] = []
        self._folded = 0  # 累计折叠的消息数
        self.summary: str = ""  # 被折叠出去的部分的摘要（真实系统由模型生成，这里用固定文案）

    def append(self, msg: dict[str, str]) -> None:
        self.messages.append(msg)
        self._trim()

    def _trim(self) -> None:
        folded = 0
        while len(self.messages) > self.max_messages:
            self.messages.pop(0)
            folded += 1
        if folded:
            self._folded += folded
            self.summary = (
                f"（早前 {self._folded} 条消息已折叠为摘要："
                "会话开头在讨论本周运动计划）"
            )

    def context(self, system: str) -> list[dict[str, str]]:
        """组装要发给模型的上下文：system + 摘要 + 窗口内消息。"""
        parts = [{"role": "system", "content": system}]
        if self.summary:
            parts.append({"role": "system", "content": self.summary})
        return parts + self.messages


def chars(messages: list[dict[str, str]]) -> int:
    """上下文的字符总数，用来对比“整段塞进”和“摘要注入”的代价。"""
    return sum(len(m["content"]) for m in messages)


# 构造“二十天完整聊天记录”，用于路径 C 的长度对比
def build_history(days: int = 20) -> list[dict[str, str]]:
    history = []
    for day in range(1, days + 1):
        history.append({"role": "user", "content": f"第{day}天：帮我看看今天要不要跑步"})
        history.append({"role": "assistant", "content": f"第{day}天回复：根据天气和安排，建议慢跑 20 分钟"})
    return history


class MemoryAwareLLM:
    """假模型：把召回的记忆和工具描述一起读，再决定用哪个工具。

    真实模型靠语义理解“记忆 + 描述”，机制相同——记忆先于决策进入上下文，
    所以一条错误的记忆会带偏后续所有决策。
    """

    def choose(self, goal: str, recalled: list[MemoryEntry]) -> str:
        joined = " ".join(e.fact for e in recalled)
        if "运动" in goal and "不" in joined:
            return "search_preferences"  # 被“用户不爱运动”这条错误记忆带偏
        return "search_records"


def main() -> None:
    print("路径 A：短期记忆的窗口与修剪")
    buffer = SessionBuffer(max_messages=8)
    for _ in range(6):
        buffer.append({"role": "user", "content": "再加一条今天的状态"})
        buffer.append({"role": "assistant", "content": "好的，已记录。"})
    print(f"窗口上限 {buffer.max_messages}，实际消息 {len(buffer.messages)} 条")
    print("摘要：", buffer.summary)
    print(f"发给模型的上下文条数：{len(buffer.context('你是生活管家'))}")
    print()

    print("路径 B：长期记忆的写入规则")
    memory = LongTermMemory()
    print(
        "用户明确说 ->",
        memory.remember(
            MemoryEntry("pref:sport", "用户偏爱运动，例如晨跑", source="user", confidence=1.0)
        ),
    )
    print(
        "模型低置信度推断 ->",
        memory.remember(
            MemoryEntry("habit:study", "用户可能在用番茄钟学习", source="model_inference", confidence=0.5)
        ),
    )
    print(
        "同 key 冲突 ->",
        memory.remember(
            MemoryEntry("pref:sport", "用户偏爱夜跑", source="user", confidence=1.0)
        ),
    )
    print("召回「运动」：", [e.fact for e in memory.recall("运动")])
    print()

    print("路径 C：整段历史 vs 摘要注入——模型都答对了，输入差了一个量级")
    history = build_history()
    full = history  # 二十天整段塞进
    injected = memory.recall("运动")  # 只召回相关偏好
    print(f"整段塞进：{chars(full)} 字符，{len(full)} 条消息")
    print(f"摘要注入：{chars([{'content': e.fact} for e in injected])} 字符，1 条偏好")
    print()

    print("路径 D：一条错误记忆带偏决策，回滚后恢复正常")
    memory_d = LongTermMemory()  # 新场景：单独一份记忆库，避免路径 B 的冲突规则挡路
    memory_d.remember(
        MemoryEntry(
            "pref:sport",
            "用户不喜欢运动，别主动推荐跑步",
            source="model_inference",
            confidence=0.9,
            reviewed=True,  # 审核过了，但来源是过期的推断——审核不是万能
        )
    )
    llm = MemoryAwareLLM()
    picked = llm.choose("查看这周运动记录", memory_d.recall("运动"))
    print("带偏决策：模型选了", picked, "（本该查运动记录，却去查偏好了）")
    print(
        "定位：这条记忆来源是", memory_d.entries["pref:sport"].source,
        "，与用户今天明确想看运动矛盾",
    )
    print(memory_d.revoke("pref:sport"))
    memory_d.remember(
        MemoryEntry("pref:sport", "用户今天明确说要看运动记录", source="user", confidence=1.0)
    )
    picked = llm.choose("查看这周运动记录", memory_d.recall("运动"))
    print("修正后决策：模型选了", picked)


# ===== 课后作业：学习资料记忆库的召回排序与冲突更新 =====

STUDY_MEMORY = LongTermMemory()
STUDY_MEMORY.remember(
    MemoryEntry("pref:study", "用户偏好用番茄钟学习", source="user", confidence=1.0)
)
STUDY_MEMORY.remember(
    MemoryEntry("weak:recite", "用户对“费曼技巧”掌握一般", source="tool_observation", confidence=0.8, reviewed=True)
)


def recall_top(memory: LongTermMemory, keyword: str, top_k: int = 3) -> list[MemoryEntry]:
    """TODO 作业 1：按置信度降序返回命中的前 top_k 条记忆。"""
    raise NotImplementedError("请完成 recall_top")


def update_fact(memory: LongTermMemory, key: str, new_fact: str, source: str) -> str:
    """TODO 作业 2：同 key 的冲突更新——
    source 为 "user" 时直接覆盖并返回"已更新"；
    否则返回"需要审核，未覆盖"（不让一条推断悄悄改掉用户声明的事实）。
    """
    raise NotImplementedError("请完成 update_fact")


def homework() -> None:
    print("召回排序（应把置信度高的放在前面）：")
    for entry in recall_top(STUDY_MEMORY, "学习", top_k=2):
        print(" ", entry.key, entry.fact, entry.confidence)
    print("用户改口（应覆盖）：", update_fact(STUDY_MEMORY, "pref:study", "改用卡片法学习", "user"))
    print("模型猜测（应拒绝覆盖）：", update_fact(STUDY_MEMORY, "pref:study", "用户可能改用卡片法", "model_inference"))
    print("最终记忆：", STUDY_MEMORY.entries["pref:study"].fact)


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
