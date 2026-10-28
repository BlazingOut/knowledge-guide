from fastapi import FastAPI


# 创建一个 FastAPI 应用对象。变量名 app 是启动命令要寻找的名字。
app = FastAPI(title="FastAPI 学习练习")


# 把下面的 Python 函数注册为 GET /hello 接口。
@app.get("/hello")
def say_hello(name: str = "朋友"):
    """根据 name 生成一条问候语。"""
    if name == "myy":
        message = "你好，朋友"
    else:
        message = f"你好，{name}"

    return {"message": message}


@app.get("/health")
def health_check():
    return {"status": "ok"}


# TODO 作业 1：新增一个 GET /goodbye 接口。
# TODO 作业 2：让接口返回一条告别消息。
# TODO 作业 3：让 /goodbye?name=小明 返回包含 name 的告别消息。
