import asyncio
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel


app = FastAPI(title="FastAPI 第九课")


class ChatInput(BaseModel):
    message: str


class ChatOutput(BaseModel):
    answer: str


class FakeModelClient:
    """用 asyncio.sleep 模拟一个异步模型服务。"""

    async def complete(self, message: str, delay: float = 0.2) -> str:
        await asyncio.sleep(delay)
        if message == "fail":
            raise RuntimeError("模拟的模型服务失败")
        return f"模型收到：{message}"


model_client = FakeModelClient()


@app.post("/chat", response_model=ChatOutput)
async def chat(
    payload: ChatInput,
    delay: Annotated[float, Query(ge=0, le=5)] = 0.2,
):
    try:
        async with asyncio.timeout(2):
            answer = await model_client.complete(payload.message, delay)
    except TimeoutError:
        raise HTTPException(status_code=504, detail="模型服务超时")
    except RuntimeError:
        raise HTTPException(status_code=502, detail="模型服务暂时不可用")

    return ChatOutput(answer=answer)


# ===== 课后作业 =====

def homework() -> None:
    """作业要求写在课件中；默认入口不执行作业。"""
    raise NotImplementedError("请根据课件完成作业")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("lesson09_async:app", host="127.0.0.1", port=8008, reload=True)
