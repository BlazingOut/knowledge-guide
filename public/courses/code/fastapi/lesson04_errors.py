from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel

app = FastAPI(title="FastAPI 第四课")

class RenameInput(BaseModel):
    name: str

@app.get("/life-items/{item_id}")
def get_life_item(item_id: int):
    if item_id != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"找不到生活事项 {item_id}")
    return {"id": 1, "content": "买咖啡"}

@app.post("/life-items/{item_id}/rename")
def rename_life_item(item_id: int, payload: RenameInput):
    if item_id != 1:
        raise HTTPException(status_code=404, detail="生活事项不存在")
    if not payload.name.strip():
        raise HTTPException(status_code=400, detail="名称不能为空")
    return {"id": item_id, "name": payload.name.strip()}


# TODO 作业 1：新增 GET /status 接口。
# TODO 作业 2：让它返回 {"status": "ok"}。
# TODO 作业 3：让 /status/{code} 接收一个整数路径参数。
# TODO 作业 4：当 code 不是 200 时抛出 HTTPException。
# TODO 作业 5：在 /docs 中测试正确和错误的 code。
