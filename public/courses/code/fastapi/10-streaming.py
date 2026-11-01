import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel


app = FastAPI(title="FastAPI 第十课")


class ChatInput(BaseModel):
    message: str


async def fake_model_stream(message: str) -> AsyncIterator[str]:
    """逐段产生模拟模型输出。"""
    for part in [f"你说的是：{message}", "。这是", "一条流式", "响应。"]:
        await asyncio.sleep(0.2)
        yield part


async def event_stream(message: str) -> AsyncIterator[str]:
    try:
        async for part in fake_model_stream(message):
            yield f"data: {part}\n\n"
        yield "event: done\ndata: [DONE]\n\n"
    except asyncio.CancelledError:
        # 客户端断开时停止后续生成。
        raise


@app.post("/chat/stream")
async def chat_stream(payload: ChatInput):
    return StreamingResponse(
        event_stream(payload.message),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


# ===== 课后作业 =====

def homework() -> None:
    """作业要求写在课件中；默认入口不执行作业。"""
    raise NotImplementedError("请根据课件完成作业")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8009)
