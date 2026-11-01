"""第一课示例：Agent 概念对照，以及 OpenAI 兼容接口调用 DeepSeek。"""

from __future__ import annotations

import os

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc, assignment]


DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-chat"


# ===== 课程示例：打印 Prompt，并演示一次调用 =====


def demo_chat(messages: list[dict[str, str]]) -> str:
    """课程示例用的一轮调用，假定 messages 已合法。"""
    if OpenAI is None:
        raise RuntimeError("请先安装 openai：pip install openai")
    api_key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("缺少环境变量 DEEPSEEK_API_KEY")
    client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    completion = client.chat.completions.create(
        model=DEEPSEEK_MODEL,
        messages=messages,
        temperature=0.3,
    )
    content = completion.choices[0].message.content
    if content is None:
        raise RuntimeError("模型没有返回文本")
    return content


def main() -> None:
    messages = [
        {
            "role": "system",
            "content": "你是生活管家。只用一两句中文回答，不要列表。",
        },
        {
            "role": "user",
            "content": "这周只跑步一次，还要不要加今晚的计划？",
        },
    ]
    print("将发送的 messages：")
    for item in messages:
        print(f"  [{item['role']}] {item['content']}")
    print()
    if OpenAI is None:
        print("未安装 openai，跳过真实调用。")
        return
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        print("未设置 DEEPSEEK_API_KEY，跳过真实调用。")
        return
    print("助手回复：", demo_chat(messages))


# ===== 课后作业：两轮对话 =====
# 不要复制 demo_chat 换个名字交差：必须做参数校验，并组出带历史的第二轮。


def chat(messages: list[dict[str, str]]) -> str:
    """调用 DeepSeek，返回助手文本。

    要求：
    1. messages 为空则 ValueError；
    2. 每条含 role、content，role 只能是 system/user/assistant；
    3. 缺少 DEEPSEEK_API_KEY 则 RuntimeError；
    4. base_url 为 https://api.deepseek.com，model 为 deepseek-chat；
    5. content 为 None 时 RuntimeError。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 chat")


def build_second_turn(
    first_user: str,
    first_reply: str,
    second_user: str,
) -> list[dict[str, str]]:
    """构造第二轮 messages：system + 第一轮 user/assistant + 第二轮 user。

    任一字符串去空白后为空则 ValueError。
    system 内容：你是生活管家。只用一两句中文回答，不要列表。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 build_second_turn")


def homework() -> None:
    """完成 TODO 后取消 __main__ 中的注释。"""
    first_user = "这周只跑步一次，够不够？"
    first_messages = [
        {
            "role": "system",
            "content": "你是生活管家。只用一两句中文回答，不要列表。",
        },
        {"role": "user", "content": first_user},
    ]
    first_reply = chat(first_messages)
    print("第一轮用户：", first_user)
    print("第一轮助手：", first_reply)
    second_user = "那帮我起一个今晚补练的标题。"
    second_messages = build_second_turn(first_user, first_reply, second_user)
    print("第二轮将发送的 roles：", [item["role"] for item in second_messages])
    second_reply = chat(second_messages)
    print("第二轮用户：", second_user)
    print("第二轮助手：", second_reply)


if __name__ == "__main__":
    main()
    # 完成作业后取消下一行注释：
    # homework()
