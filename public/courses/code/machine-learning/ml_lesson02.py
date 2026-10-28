"""第二课示例：平方损失的梯度，以及学习率、小批量各改变哪一步。"""

# ===== 课程示例：ŷ = w * x 的均方误差和梯度下降 =====
# 只有一个特征（面积）和一个参数（系数），方便把一步更新算完。
# 多特征、常数项和正规方程不属于本课。

Row = tuple[float, float]
# (面积, 成交价万元)

# 四条按面积准备的样本。数值小，是为了让学习率的三种结果能在少数几步里看出来。
ROWS: list[Row] = [
    (50.0, 100.0),
    (80.0, 200.0),
    (100.0, 180.0),
    (120.0, 260.0),
]


def predict(x: float, weight: float) -> float:
    """当前参数下的预测价：面积乘以系数。"""
    return weight * x


def mean_squared_error(rows: list[Row], weight: float) -> float:
    """全部样本的平均平方误差。rows 为空时抛出 ValueError。"""
    if not rows:
        raise ValueError("至少需要一条样本才能计算平均损失")
    total = 0.0
    for x, y in rows:
        gap = y - predict(x, weight)
        total += gap * gap
    return total / len(rows)


def squared_error_gradient(x: float, y: float, weight: float) -> float:
    """返回 (y - w*x)^2 对 weight 的导数，即 -2 * (y - ŷ) * x。

    不修改 weight。梯度为负表示增大 weight 会降低这一条的损失。
    """
    gap = y - predict(x, weight)
    return -2.0 * gap * x


def full_batch_gradient(rows: list[Row], weight: float) -> float:
    """全部样本梯度的平均，供批量梯度下降使用。"""
    if not rows:
        raise ValueError("至少需要一条样本才能计算梯度")
    total = 0.0
    for x, y in rows:
        total += squared_error_gradient(x, y, weight)
    return total / len(rows)


def train_full_batch(
    rows: list[Row],
    weight: float,
    learning_rate: float,
    steps: int,
) -> list[float]:
    """用全部样本的平均梯度更新 weight，返回每一步之后的平均损失。

    learning_rate 必须为正，steps 必须为正整数。
    返回列表长度为 steps。不修改 rows；weight 只在函数内部更新。
    """
    if learning_rate <= 0:
        raise ValueError("learning_rate 必须为正")
    if steps <= 0:
        raise ValueError("steps 必须为正整数")
    losses: list[float] = []
    current = weight
    for _ in range(steps):
        gradient = full_batch_gradient(rows, current)
        current = current - learning_rate * gradient
        losses.append(mean_squared_error(rows, current))
    return losses


def train_mini_batch(
    rows: list[Row],
    weight: float,
    learning_rate: float,
    batch_size: int,
    epochs: int,
) -> list[float]:
    """按当前顺序切成小批，每批更新一次；返回每个 epoch 结束时的平均损失。

    最后一批可以少于 batch_size。本函数不打乱 rows。
    """
    if learning_rate <= 0:
        raise ValueError("learning_rate 必须为正")
    if batch_size <= 0:
        raise ValueError("batch_size 必须为正整数")
    if epochs <= 0:
        raise ValueError("epochs 必须为正整数")
    losses: list[float] = []
    current = weight
    for _ in range(epochs):
        for start in range(0, len(rows), batch_size):
            batch = rows[start : start + batch_size]
            gradient = full_batch_gradient(batch, current)
            current = current - learning_rate * gradient
        losses.append(mean_squared_error(rows, current))
    return losses


def main() -> None:
    x, y = 80.0, 200.0
    weight = 2.0
    print(f"单条样本：面积 {x}，成交价 {y}，系数 {weight}")
    print(f"  预测 {predict(x, weight)}，损失 {(y - predict(x, weight)) ** 2}")
    print(f"  梯度 {squared_error_gradient(x, y, weight)}")
    print()
    print(f"全部 {len(ROWS)} 条的初始平均损失：{mean_squared_error(ROWS, weight):.2f}")
    print()
    for rate in (1e-8, 1e-5, 1e-3):
        losses = train_full_batch(ROWS, weight, rate, steps=5)
        shown = ", ".join(f"{loss:.1f}" for loss in losses)
        print(f"学习率 {rate:g} 的五步损失：{shown}")
    print()
    mini = train_mini_batch(ROWS, weight, learning_rate=1e-5, batch_size=2, epochs=3)
    shown = ", ".join(f"{loss:.1f}" for loss in mini)
    print(f"batch size 2、学习率 1e-5，三个 epoch 结束时的损失：{shown}")
    print("每个 epoch 有 4 条样本，所以更新 2 次，不是 4 次，也不是 1 次。")


# ===== 课后作业：两个特征的梯度，以及一个 epoch 的小批量 =====
# 示例只有面积一个系数。作业的预测改成：
#   ŷ = w1 * 面积 + w2 * 房龄
# 没有常数项。损失仍是单条平方误差 (y - ŷ)^2。

Sample = tuple[float, float, float]
# (面积, 房龄, 成交价万元)

HOMEWORK_ROWS: list[Sample] = [
    (50.0, 10.0, 120.0),
    (80.0, 8.0, 200.0),
    (70.0, 20.0, 150.0),
    (100.0, 5.0, 240.0),
]


def row_gradients(
    area: float,
    age: float,
    price: float,
    weight_area: float,
    weight_age: float,
) -> tuple[float, float]:
    """返回这一条样本上，平方误差对 weight_area 和 weight_age 的偏导数。

    预测 ŷ = weight_area * area + weight_age * age。
    两个分量分别是 -2 * (price - ŷ) * area 和 -2 * (price - ŷ) * age。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 row_gradients")


def mini_batch_epoch(
    rows: list[Sample],
    weight_area: float,
    weight_age: float,
    learning_rate: float,
    batch_size: int,
) -> tuple[float, float]:
    """按 rows 的当前顺序跑完一个 epoch，返回更新后的 (weight_area, weight_age)。

    每批用该批样本的平均梯度更新一次。最后一批可以不足 batch_size。
    不要在函数内部打乱 rows。
    learning_rate 小于等于 0，或 batch_size 小于 1 时，抛出 ValueError。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 mini_batch_epoch")


def homework() -> None:
    """完成后运行：先看一条样本的两个梯度分量，再看一个 epoch 之后的权重。"""
    area, age, price = HOMEWORK_ROWS[1]
    print("第二条样本的梯度分量：", row_gradients(area, age, price, 1.0, 1.0))
    updated = mini_batch_epoch(
        HOMEWORK_ROWS,
        weight_area=1.0,
        weight_age=1.0,
        learning_rate=1e-5,
        batch_size=2,
    )
    print("一个 epoch 之后的 (面积系数, 房龄系数)：", updated)
    print("batch size 为 2、样本 4 条，这个 epoch 里应更新 2 次。")


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
