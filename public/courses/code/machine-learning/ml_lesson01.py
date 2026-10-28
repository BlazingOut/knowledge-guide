"""第一课示例：一条监督学习记录，以及按时间把样本切成三份。"""

# ===== 课程示例：房价成交表里的特征、标签和数据集 =====
# 本课不估计参数，也不计算误差。
# 表中每一行是一条样本。预测成交价时，面积和房龄是特征，成交价是标签。
# 小区和月份用来说明"这条样本是谁、发生在何时"，并决定它落入哪一份数据。

Sale = tuple[str, int, float, int, float]
# (小区, 成交月份 YYYYMM, 面积, 房龄, 成交价万元)

SALES: list[Sale] = [
    ("梧桐", 202401, 78.0, 10, 290.0),
    ("梧桐", 202402, 89.0, 9, 318.0),
    ("连园", 202403, 66.0, 15, 240.0),
    ("梧桐", 202404, 102.0, 8, 360.0),
    ("连园", 202405, 80.0, 14, 275.0),
    ("江岸", 202406, 95.0, 5, 410.0),
    ("连园", 202407, 70.0, 16, 255.0),
    ("江岸", 202408, 110.0, 4, 455.0),
    ("梧桐", 202409, 85.0, 11, 305.0),
    ("江岸", 202410, 88.0, 6, 390.0),
]


def feature_and_label(row: Sale) -> tuple[tuple[float, int], float]:
    """从一条成交记录中取出本课使用的特征和标签。

    输入 row 是 (小区, 月份, 面积, 房龄, 成交价)。
    返回 ((面积, 房龄), 成交价)。小区和月份不进入特征向量：
    月份只用于切分，小区留到作业里作为切分单位。
    """
    _district, _month, area, age, price = row
    return (area, age), price


def split_rows(
    rows: list[Sale],
    validation_count: int,
    test_count: int,
) -> tuple[list[Sale], list[Sale], list[Sale]]:
    """按已排好的时间顺序，把末尾样本划给验证集和测试集。

    rows 必须按成交月份从早到晚排列。
    validation_count、test_count 是从末尾截走的条数，要求都是非负整数，
    且两者之和小于 len(rows)，保证训练集至少有一条。
    返回 (训练集, 验证集, 测试集)。不修改 rows。
    测试集是最近的 test_count 条；验证集是它前面的 validation_count 条。
    """
    if validation_count < 0 or test_count < 0:
        raise ValueError("validation_count 和 test_count 必须是非负整数")
    if validation_count + test_count >= len(rows):
        raise ValueError("训练集至少要留下一条样本")
    test_start = len(rows) - test_count
    validation_start = test_start - validation_count
    training = rows[:validation_start]
    validation = rows[validation_start:test_start]
    test = rows[test_start:]
    return training, validation, test


def describe_split(name: str, rows: list[Sale]) -> None:
    """打印一份数据里每条样本的特征、标签和月份。"""
    print(f"--- {name}：{len(rows)} 条 ---")
    for row in rows:
        features, label = feature_and_label(row)
        print(f"  月份 {row[1]}  小区 {row[0]}  特征 x={features}  标签 y={label}")


def main() -> None:
    training, validation, test = split_rows(SALES, validation_count=3, test_count=2)
    print("参数 w：面积系数、房龄系数、常数项。本课只命名，不估计数值。")
    print("预测时输入 x=(面积, 房龄)，输出 ŷ；标签 y 是成交价。")
    print()
    describe_split("训练集（只在这里调整 w）", training)
    describe_split("验证集（比较模型设定，不更新 w）", validation)
    describe_split("测试集（选定之后看一次）", test)
    print()
    last_training_month = training[-1][1]
    first_later_month = min(row[1] for row in validation + test)
    print(
        f"时间顺序：训练集最后月份 {last_training_month}，"
        f"验证集和测试集最早月份 {first_later_month}。"
    )


# ===== 课后作业：换标签，并按小区切分 =====
# 示例把"成交价"当作回归标签，并按时间切分。
# 作业要做两件不同的事：
# 1. 同一个表既能取出成交价，也能取出"相对本小区训练集价位的高/低"；
# 2. 切分时同一个小区的房子必须整组进入同一份数据。

def records_for_task(
    rows: list[Sale],
    task: str,
    training_rows: list[Sale],
) -> list[tuple[tuple[float, int], float | str]]:
    """按任务返回 (特征, 标签) 列表，顺序与 rows 相同。

    task 只能是 "price" 或 "district_price_level"。
    "price"：标签是成交价（float）。
    "district_price_level"：用 training_rows 里每个小区的成交价中位数，
    把 rows 中该小区的样本标成 "高" 或 "低"。成交价等于中位数时标 "低"。
    中位数只从 training_rows 计算，不能使用 rows 里其余样本的价格。
    某个小区在 training_rows 中没有样本时，抛出 ValueError。
    特征仍然是 (面积, 房龄)。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 records_for_task")


def split_by_district(
    rows: list[Sale],
) -> tuple[list[Sale], list[Sale], list[Sale]]:
    """按小区把样本分进训练集、验证集、测试集。

    同一个小区的所有样本必须落在同一份数据中。
    小区的顺序按它在 rows 里第一次出现的次序。
    按这个次序把小区依次分给三份数据，使三份的小区数尽可能接近，
    并且训练集的小区数不少于验证集和测试集。
    返回 (训练集, 验证集, 测试集)，每份内部保持 rows 中的原有相对顺序。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 split_by_district")


def homework() -> None:
    """完成两个函数后运行，检查标签形状和小区是否被拆开。"""
    training, validation, test = split_by_district(SALES)
    print("按小区切分后的小区名单：")
    for name, part in ("训练集", training), ("验证集", validation), ("测试集", test):
        districts = []
        for row in part:
            if row[0] not in districts:
                districts.append(row[0])
        print(f"  {name}：{districts}")

    print()
    print("价格任务的前两条 (x, y)：")
    for item in records_for_task(training, "price", training)[:2]:
        print(" ", item)

    print("价位任务在训练集上的标签计数：")
    levels = records_for_task(training, "district_price_level", training)
    high = sum(1 for _features, label in levels if label == "高")
    low = sum(1 for _features, label in levels if label == "低")
    print(f"  高={high}  低={low}  总条数={len(levels)}")


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
