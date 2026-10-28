"""第一课示例：异常与错误处理。"""

class InvalidRecordError(ValueError):
    """记录内容不符合业务规则。"""

class RecordNotFoundError(LookupError):
    """找不到请求的记录。"""

def validate_content(content: str) -> None:
    if not content.strip():
        raise InvalidRecordError("记录内容不能为空")

def parse_kind(text: str) -> str:
    kind = text.strip().lower()
    if not kind:
        raise InvalidRecordError("记录类型不能为空")
    return kind

def find_record(records: list[dict[str, object]], index: int) -> dict[str, object]:
    try:
        return records[index]
    except IndexError as error:
        raise RecordNotFoundError(f"记录下标不存在：{index}") from error

def main() -> None:
    records = [{"content": "买咖啡", "kind": "shopping"}]
    for content, kind_text, index in [("跑步", "health", 0), ("", "life", 0), ("读书", "", 0), ("读书", "life", 3)]:
        try:
            validate_content(content)
            kind = parse_kind(kind_text)
            record = find_record(records, index)
        except InvalidRecordError as error:
            print(f"输入错误：{error}")
        except RecordNotFoundError as error:
            print(f"查找失败：{error}")
        else:
            print("处理成功：", record, kind)

 # ===== 课后作业：书签收藏 =====

class InvalidBookmarkError(ValueError):
    """书签标题或地址不符合规则。"""

class DuplicateBookmarkError(ValueError):
    """书签地址已经存在。"""

def validate_bookmark(title: str, url: str) -> tuple[str, str]:
    title, url = title.strip(), url.strip()
    if not title:
        raise InvalidBookmarkError("书签标题不能为空")
    if not url.startswith(("http://", "https://")):
        raise InvalidBookmarkError("书签地址必须以 http:// 或 https:// 开头")
    return title, url

def validate_duplicate_url(bookmarks: list[dict[str, str]], url: str) -> None:
    if any(item["url"] == url for item in bookmarks):
        raise DuplicateBookmarkError("书签地址已经存在")

def add_bookmark(bookmarks: list[dict[str, str]], title: str, url: str) -> None:
    title, url = validate_bookmark(title, url)
    validate_duplicate_url(bookmarks, url)
    bookmarks.append({"title": title, "url": url})

def open_bookmark(bookmarks: list[dict[str, str]], title: str) -> str:
    title = title.strip()
    for item in bookmarks:
        if item["title"] == title:
            return item["url"]
    raise LookupError(f"找不到书签：{title}")

def homework() -> None:
    bookmarks: list[dict[str, str]] = []
    try:
        add_bookmark(bookmarks, " 三体 ", " https://book.com/threebody ")
    except (InvalidBookmarkError, DuplicateBookmarkError) as error:
        print(f"添加失败：{error}")
    else:
        print("添加成功：", bookmarks[-1])

    try:
        add_bookmark(bookmarks, "资本论", "book.com/capitalization")
    except InvalidBookmarkError as error:
        print(f"地址无效：{error}")

    try:
        add_bookmark(bookmarks, "三体新版", "https://book.com/threebody")
    except DuplicateBookmarkError as error:
        print(f"重复书签：{error}")

    try:
        print("找到书签：", open_bookmark(bookmarks, " 三体 "))
    except LookupError as error:
        print(f"查找失败：{error}")

    try:
        open_bookmark(bookmarks, "不存在的书")
    except LookupError as error:
        print(f"查找失败：{error}")

    print("最终书签：", bookmarks)

if __name__ == "__main__":
    main()
    homework()
