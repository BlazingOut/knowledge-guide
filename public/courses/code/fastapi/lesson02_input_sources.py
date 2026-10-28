from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="FastAPI 第二课")

@app.get("/search")
def search(keyword: str, limit: int = 10):
    return {"source": "查询参数", "keyword": keyword, "limit": limit}

@app.get("/users/{user_id}")
def get_user(user_id: int):
    return {"source": "路径参数", "user_id": user_id}

class NoteInput(BaseModel):
    content: str
    category: str = "未分类"

@app.post("/notes")
def create_note(note: NoteInput):
    return {"source": "请求体", "saved_note": note}


# TODO 作业 1：给 search 增加一个可选的 category 查询参数。
# TODO 作业 2：在返回结果中加入 category。
# TODO 作业 3：分别测试提供和不提供 category 时的结果。
