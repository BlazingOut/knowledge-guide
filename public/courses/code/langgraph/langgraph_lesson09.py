"""LangGraph 第九课：Agentic RAG：检索作为工具。

把阶段 9 / RAG 课的"固定流程 RAG"升级成"检索即工具"的图：
判断要不要检索 → 检索 → 判断结果够不够 → 不够则改写查询重检索，够了就生成。
全部离线可跑：检索用"词表 + Jaccard 相似度"模拟向量检索（真实场景是
embedding + 向量库），模型节点用脚本化替身（不需要 API Key）。

演示：
- 演示 A：固定流程 RAG 基线——一次检索、不管分数直接生成（难查询召回差）；
- 演示 B：检索工具化——retrieve 是 @tool，脚本化模型决定"要不要检索"；
- 演示 C：Agentic RAG 图——判断 → 检索 → 质量判断 →（不足）改写 → 重检 → 生成，
  打印每一步的检索分数变化（0.25 → 0.75）；
- 演示 D：同一个难查询在固定 RAG 和 Agentic RAG 下的对比。

运行：
    python code/langgraph/langgraph_lesson09.py
"""

from typing import TypedDict

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode


# ---------- 1. 模拟检索：词表 + 关键词抽取 + Jaccard 相似度 ----------
# 真实场景里这一步是 embedding + 向量库（阶段 9 / RAG 课内容）；
# 本课用词表模拟"查询和文档的语义匹配"，聚焦图的形态，不重讲检索本身。

VOCAB = ["睡眠", "失眠", "睡不着", "咖啡因", "运动", "跑步", "卡路里",
         "饮食", "发票", "报销", "午休"]

# 知识库：每段文档手工打了"主题标签"（模拟 embedding 语义），正文是要检索的片段
DOCS = [
    ("d1", {"午休"}, "午休 20 分钟能提升下午效率，避免在饭后立刻午休。"),
    ("d2", {"睡眠", "失眠", "睡不着", "咖啡因"}, "每天保证 7 小时睡眠，睡前 2 小时避免咖啡因，睡前不要看手机。"),
    ("d3", {"运动", "跑步", "卡路里"}, "每周至少 150 分钟中等强度运动，跑步、游泳、骑车都可以。"),
    ("d4", {"饮食"}, "三餐规律，蛋白质每天 1.2g/kg，少油少盐。"),
    ("d5", {"发票", "报销"}, "发票报销需在 30 天内提交，发票抬头必须为公司全称。"),
]

# 改写扩展表：模拟 rewrite 模型把"口语词"翻译成知识库措辞
REWRITE_EXPAND = {
    "睡不着": ["睡眠", "失眠"],
    "失眠": ["睡眠", "睡不着"],
    "跑步": ["运动"],
    "发票": ["报销"],
}


def extract_keywords(text: str) -> set:
    """从查询里抽知识库相关词（子串匹配词表，模拟 embedding 的语义匹配）。"""
    return {w for w in VOCAB if w in text}


def jaccard(a: set, b: set) -> float:
    """Jaccard 相似度：交集大小 / 并集大小，0~1。"""
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def search(query: str, top_k: int = 1) -> list:
    """检索：抽关键词 → 对每段文档算相似度 → 按分数降序返回 [(did, body, score)]。"""
    q = extract_keywords(query)
    if not q:
        return []
    scored = sorted(
        ((jaccard(q, tags), did, body) for did, tags, body in DOCS),
        reverse=True,
    )
    return [(did, body, round(score, 2)) for score, did, body in scored[:top_k]]


@tool
def retrieve(query: str, top_k: int = 1) -> str:
    """从生活管家知识库检索与问题最相关的片段（含相关度分数）。

    查询是用户原话或改写后的查询；返回格式 "来源编号 相关度 片段正文"。
    知识库覆盖：睡眠、运动、饮食、报销、午休。
    """
    hits = search(query, top_k)
    if not hits:
        return "知识库没有与查询相关的内容"
    return "\n".join(f"[{did}] 相关度{score:.2f} {body}" for did, body, score in hits)


# ---------- 2. 固定流程 RAG 基线（演示 A） ----------


def fixed_rag(query: str):
    """固定流程 RAG：一次检索 → 不管分数，直接拿最高分片段生成。

    脚本化"生成"：把片段正文套进回答模板。固定流程的问题就在这里——
    难查询召回分数只有 0.25，证据很弱，但它没有第二次机会。
    """
    hits = search(query)
    if not hits:
        return "知识库没有相关内容", 0.0, "（未检索）"
    did, body, score = hits[0]
    answer = f"根据知识库：{body}（来源 {did}，相关度 {score:.2f}）"
    return answer, score, f"一次检索命中 {did}"


# ---------- 3. Agentic RAG 图（演示 C） ----------


class RAGState(TypedDict):
    query: str            # 原始问题
    rewritten: str        # 当前查询（初始 = 原句；改写后更新）
    needs_retrieval: bool  # 判断节点的决策：要不要检索
    hits: list            # 检索命中的 [(did, body, score)]
    best_score: float     # 本次检索的最高分
    attempts: int         # 已检索次数（重试上限用）
    quality_ok: bool      # 质量判断的结论
    answer: str           # 最终回答


MAX_ATTEMPTS = 2  # 最多检索几次（含改写重检）——图的终止条件之一


def node_decide(state: RAGState) -> dict:
    """判断节点（脚本化模型）：查询涉及知识库才检索。

    这是 Agentic RAG 和固定流程的第一个区别：固定流程每次都检索，
    这里由"模型"决定要不要检索（"你好"这类问题直接答，不浪费一次检索）。
    """
    keywords = extract_keywords(state["query"])
    needs = len(keywords) > 0
    print(f"[decide] 查询涉及知识库词 {sorted(keywords)} -> {'去检索' if needs else '跳过检索，直接回答'}")
    return {"needs_retrieval": needs}


def route_decide(state: RAGState) -> str:
    return "retrieve" if state["needs_retrieval"] else "generate"


def node_retrieve(state: RAGState) -> dict:
    """检索节点：调检索工具（图形态里检索是编排好的固定一步，不靠模型临场发挥）。"""
    hits = search(state["rewritten"])
    best = hits[0][2] if hits else 0.0
    print(f"[retrieve] 查询={state['rewritten']!r} -> 最高相关度 {best:.2f}"
          + (f"，命中 {hits[0][0]}" if hits else "，无命中"))
    return {"hits": hits, "best_score": best, "attempts": state["attempts"] + 1}


def node_quality(state: RAGState) -> dict:
    """质量判断节点（规则）：分数够 / 次数到上限 → 生成；否则去改写。"""
    ok = state["best_score"] >= 0.5 or state["attempts"] >= MAX_ATTEMPTS
    reason = "分数够" if state["best_score"] >= 0.5 else (
        "已达重试上限" if state["attempts"] >= MAX_ATTEMPTS else "分数不够")
    print(f"[quality] 相关度 {state['best_score']:.2f} / 已检索 {state['attempts']} 次"
          f"（上限 {MAX_ATTEMPTS}）-> {reason}，{'生成' if ok else '改写重检'}")
    return {"quality_ok": ok}


def route_quality(state: RAGState) -> str:
    return "generate" if state["quality_ok"] else "rewrite"


def node_rewrite(state: RAGState) -> dict:
    """改写节点（脚本化模型）：把口语词扩展成知识库措辞，生成新查询。

    真实实现里这里是调一次模型（成本 +1）；本课用扩展表模拟"口语 → 知识库语言"。
    """
    keywords = extract_keywords(state["rewritten"])
    expanded = set(keywords)
    for kw in keywords:
        expanded.update(REWRITE_EXPAND.get(kw, []))
    new_query = " ".join(sorted(expanded))
    print(f"[rewrite] {state['rewritten']!r} -> {new_query!r}")
    return {"rewritten": new_query}


def node_generate(state: RAGState) -> dict:
    """生成节点（脚本化模型）：没检索就答问候；有检索就引用证据生成。"""
    if not state["needs_retrieval"]:
        answer = "你好！我是生活管家，可以问我睡眠、运动、饮食、报销等问题。"
        print("[generate] 未检索，直接回答问候")
        return {"answer": answer}
    if state["hits"]:
        did, body, score = state["hits"][0]
        answer = f"根据知识库：{body}（来源 {did}，相关度 {score:.2f}）"
    else:
        answer = "知识库没有相关内容，建议换个问法。"
    print(f"[generate] 用最高分片段生成（相关度 {state['best_score']:.2f}）")
    return {"answer": answer}


def build_agentic_rag_graph():
    """Agentic RAG 图：decide →(要检索?)→ retrieve → quality →(够?)→ generate | rewrite →(重检)→ retrieve。"""
    graph = StateGraph(RAGState)
    graph.add_node("decide", node_decide)
    graph.add_node("retrieve", node_retrieve)
    graph.add_node("quality", node_quality)
    graph.add_node("rewrite", node_rewrite)
    graph.add_node("generate", node_generate)
    graph.add_edge(START, "decide")
    graph.add_conditional_edges("decide", route_decide)       # 检索决策
    graph.add_edge("retrieve", "quality")
    graph.add_conditional_edges("quality", route_quality)     # 质量判断
    graph.add_edge("rewrite", "retrieve")                     # 重检索回路
    graph.add_edge("generate", END)
    return graph.compile()


# ---------- 演示 ----------


def demo_fixed_rag():
    """演示 A：固定流程 RAG——一次检索，不管分数直接生成。"""
    print("--- 演示 A：固定流程 RAG（基线） ---")
    query = "我晚上老是睡不着怎么办"
    answer, score, info = fixed_rag(query)
    print(f"查询：{query}")
    print(f"检索结果：{info}，相关度 {score:.2f}")
    print(f"生成：{answer}")
    print("问题：相关度只有 0.25，证据很弱，但没有第二次机会——这就是固定流程的局限")


def demo_retrieval_tool():
    """演示 B：检索工具化——retrieve 是 @tool，模型决定要不要调。"""
    print("--- 演示 B：检索工具化（模型按需调用） ---")

    def call_model_fake(state):
        last = state["messages"][-1]
        q = last.content
        if extract_keywords(q):
            return {"messages": [AIMessage(
                content="我去查一下知识库。",
                tool_calls=[{"name": "retrieve", "args": {"query": q}, "id": "r1"}])]}
        return {"messages": [AIMessage(content="这个问题不涉及知识库，我直接回答。")]}

    def route(state):
        last = state["messages"][-1]
        return "tools" if last.tool_calls else END

    graph = StateGraph(MessagesState)
    graph.add_node("model", call_model_fake)
    graph.add_node("tools", ToolNode([retrieve]))
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", route)
    graph.add_edge("tools", END)
    app = graph.compile()

    for q in ["我晚上老是睡不着怎么办", "你好"]:
        result = app.invoke({"messages": [HumanMessage(content=q)]})
        last = result["messages"][-1]
        print(f"  查询 {q!r} -> {type(last).__name__}: {last.content!r}")

    print("结论：检索是一个普通工具（有 schema、可被模型发起调用），"
          "'要不要检索'由模型决定——这是和固定流程的本质区别")


def demo_agentic_rag():
    """演示 C：Agentic RAG 图——判断 → 检索 → 质量判断 → 改写 → 重检 → 生成。"""
    print("--- 演示 C：Agentic RAG 图（难查询走改写重检） ---")
    app = build_agentic_rag_graph()
    final = app.invoke({
        "query": "我晚上老是睡不着怎么办",
        "rewritten": "我晚上老是睡不着怎么办",
        "needs_retrieval": False,
        "hits": [],
        "best_score": 0.0,
        "attempts": 0,
        "quality_ok": False,
        "answer": "",
    })
    print(f"最终回答：{final['answer']}")
    print(f"统计：检索 {final['attempts']} 次，最高相关度 {final['best_score']:.2f}")


def demo_compare():
    """演示 D：同一个难查询，固定 RAG vs Agentic RAG 对比。"""
    print("--- 演示 D：固定 RAG vs Agentic RAG（同一难查询） ---")
    query = "我晚上老是睡不着怎么办"
    answer, score, info = fixed_rag(query)
    print(f"[固定 RAG] 检索 1 次，相关度 {score:.2f} -> {answer}")
    app = build_agentic_rag_graph()
    final = app.invoke({
        "query": query,
        "rewritten": query,
        "needs_retrieval": False,
        "hits": [],
        "best_score": 0.0,
        "attempts": 0,
        "quality_ok": False,
        "answer": "",
    })
    print(f"[Agentic RAG] 检索 {final['attempts']} 次，最高相关度 {final['best_score']:.2f} -> {final['answer']}")


def main():
    demo_fixed_rag()
    print()
    demo_retrieval_tool()
    print()
    demo_agentic_rag()
    print()
    demo_compare()


# ===== 课后作业：终止条件、检索决策、成本对比 =====


def build_agentic_rag_with_limit(max_attempts: int):
    """作业 1：可配置重试上限的 Agentic RAG。

    提示：把 MAX_ATTEMPTS 换成参数 max_attempts 传给图里的质量判断。
    实现方式：在 build_agentic_rag_graph 的基础上，把质量判断的条件边
    改成一个读 max_attempts 的函数（用闭包或全局变量）。
    完成后用 max_attempts=1 验证：难查询第一次分数不够也会直接用现有结果生成。
    """
    # TODO：实现这个函数（参考 build_agentic_rag_graph）
    pass


def decide_no_retrieval(query: str) -> bool:
    """作业 2：检索决策——判断一个问题是否需要检索。

    规则：查询里出现知识库相关词（extract_keywords 非空）才需要检索。
    返回 True 表示需要检索。
    示例："你好" -> False；"我睡不着" -> True。
    """
    # TODO：实现这个函数
    pass


def count_model_calls_fixed(query: str) -> int:
    """作业 3：固定 RAG 的成本——模型调用次数。"""
    # 固定 RAG：只有最后生成一次模型调用
    return 1


def count_model_calls_agentic(query: str) -> int:
    """作业 3：Agentic RAG 的成本——模型调用次数（decide / rewrite / generate）。

    提示：跑一遍 demo_agentic_rag 的图，数 decide、rewrite、generate 三个
    模型节点各执行了几次（检索和质量判断是规则/工具，不算模型调用）。
    难查询走了一次改写，所以是 decide(1) + rewrite(1) + generate(1) = 3。
    """
    # TODO：实现这个函数（可以模拟：难查询 3 次，简单查询 decide+generate = 2 次）
    pass


def homework():
    """运行课后作业（完成后取消 __main__ 中的注释）。"""
    # 作业 1：重试上限
    app = build_agentic_rag_with_limit(max_attempts=1)
    final = app.invoke({
        "query": "我晚上老是睡不着怎么办",
        "rewritten": "我晚上老是睡不着怎么办",
        "needs_retrieval": False,
        "hits": [],
        "best_score": 0.0,
        "attempts": 0,
        "quality_ok": False,
        "answer": "",
    })
    assert final["attempts"] <= 1, final["attempts"]
    print("作业 1 通过：上限 1 次时不再重检，用现有结果生成")

    # 作业 2：检索决策
    assert decide_no_retrieval("你好") is False
    assert decide_no_retrieval("我睡不着") is True
    print("作业 2 通过：无知识库词不检索，有知识库词才检索")

    # 作业 3：成本对比
    fixed = count_model_calls_fixed("我晚上老是睡不着怎么办")
    agentic = count_model_calls_agentic("我晚上老是睡不着怎么办")
    assert agentic > fixed, (fixed, agentic)
    print(f"作业 3 通过：同一难查询，固定 RAG 模型调用 {fixed} 次，"
          f"Agentic RAG {agentic} 次——多出的就是判断/改写决策的成本")


if __name__ == "__main__":
    main()
    # homework()  # 完成后取消注释
