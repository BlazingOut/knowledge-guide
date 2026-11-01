from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="FastAPI 第三课")

class LifeItemInput(BaseModel):
    content: str = Field(min_length=1, max_length=100)
    kind: str = "inbox"
    priority: int = Field(default=1, ge=1, le=5)

class LifeItemOutput(BaseModel):
    id: int
    content: str
    kind: str
    priority: int

@app.post("/life-items", response_model=LifeItemOutput)
def create_life_item(item: LifeItemInput):
    return {"id": 1, "content": item.content, "kind": item.kind, "priority": item.priority, "internal_note": "这个字段不会出现在响应中"}


# TODO 作业 1：给 LifeItemInput 增加 important: bool = False 字段。
# TODO 作业 2：给 LifeItemOutput 增加 important: bool 字段。
# TODO 作业 3：在 create_life_item 的返回值中加入 item.important。
# TODO 作业 4：在 /docs 中提交 true 和 false，观察响应变化。


# ===== 直接运行 =====
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)
