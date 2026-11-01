"""第四课示例：二分类逻辑回归的交叉熵、梯度与梯度下降。"""

# ===== 课程示例：房价是否高价成交 =====
# 特征：面积、房龄；标签：1 表示成交价超过 300 万，0 表示没有。
# 预测式：z = w1*面积 + w2*房龄 + b，p = sigmoid(z)。
# 训练：全批量梯度下降，最小化平均交叉熵。

import math

Row = tuple[float, float, int]
# (面积, 房龄, 是否高价成交)

ROWS: list[Row] = [
    (50.0, 10.0, 0),
    (60.0, 12.0, 0),
    (55.0, 8.0, 0),
    (70.0, 6.0, 1),
    (80.0, 4.0, 1),
    (85.0, 3.0, 1),
    (65.0, 5.0, 1),
    (75.0, 9.0, 0),
]


def sigmoid(z: float) -> float:
    """把分数 z 压到 (0, 1)，当作正类概率。"""
    return 1.0 / (1.0 + math.exp(-z))


def predict_probability(area: float, age: float, w1: float, w2: float, b: float) -> float:
    """p = sigmoid(w1*面积 + w2*房龄 + b)。"""
    return sigmoid(w1 * area + w2 * age + b)


def cross_entropy(y: int, p: float) -> float:
    """单样本二分类交叉熵 -[y log p + (1-y) log(1-p)]。

    预测概率 p 必须落在 (0, 1) 开区间，否则 log 无定义。
    """
    if not 0.0 < p < 1.0:
        raise ValueError("p 必须在 (0, 1) 之间")
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def mean_cross_entropy(rows: list[Row], w1: float, w2: float, b: float) -> float:
    """全部样本的平均交叉熵。rows 为空时抛出 ValueError。"""
    if not rows:
        raise ValueError("至少需要一条样本")
    total = 0.0
    for area, age, y in rows:
        p = predict_probability(area, age, w1, w2, b)
        total += cross_entropy(y, p)
    return total / len(rows)


def gradient_step(
    rows: list[Row],
    weights: tuple[float, float],
    bias: float,
    learning_rate: float,
) -> tuple[tuple[float, float], float]:
    """用全部样本的平均梯度更新 (w1, w2) 和 b，返回新的 (weights, bias)。

    每个参数的平均梯度是 -2 换成交叉熵后的 (p - y) 乘以对应特征：
        dL/dwj = (1/n) Σ (p_i - y_i) * x_ij
        dL/db  = (1/n) Σ (p_i - y_i)
    learning_rate 必须为正。不修改 rows。
    """
    if learning_rate <= 0:
        raise ValueError("learning_rate 必须为正")
    n = len(rows)
    if n == 0:
        raise ValueError("至少需要一条样本")
    sum_g_w1 = 0.0
    sum_g_w2 = 0.0
    sum_g_b = 0.0
    for area, age, y in rows:
        p = predict_probability(area, age, weights[0], weights[1], bias)
        gap = p - y
        sum_g_w1 += gap * area
        sum_g_w2 += gap * age
        sum_g_b += gap
    new_w1 = weights[0] - learning_rate * sum_g_w1 / n
    new_w2 = weights[1] - learning_rate * sum_g_w2 / n
    new_b = bias - learning_rate * sum_g_b / n
    return (new_w1, new_w2), new_b


def boundary_x2(w1: float, w2: float, b: float, x1: float) -> float:
    """决策边界 x2 = -(w1*x1 + b) / w2。w2 为 0 时边界退化为竖线。"""
    if w2 == 0.0:
        raise ValueError("w2 为 0 时决策边界不是 x2 关于 x1 的直线，不适用本函数")
    return -(w1 * x1 + b) / w2


def main() -> None:
    weights = (0.0, 0.0)
    bias = 0.0
    print("初始权重 (0, 0)、b=0 时，每条样本的 p = sigmoid(0) = 0.5。")
    print(f"初始平均交叉熵：{mean_cross_entropy(ROWS, weights[0], weights[1], bias):.4f}")
    print("（应接近 0.693 = -log 0.5）")
    print()

    learning_rate = 0.002
    print(f"学习率 {learning_rate}，跑 1000 步，每 200 步打印一次：")
    for step in range(1, 1001):
        weights, bias = gradient_step(ROWS, weights, bias, learning_rate)
        if step in (1, 200, 400, 600, 800, 1000):
            loss = mean_cross_entropy(ROWS, weights[0], weights[1], bias)
            print(
                f"  第 {step:4d} 步：损失 {loss:.4f}，"
                f"w1={weights[0]:.4f} w2={weights[1]:.4f} b={bias:.4f}"
            )

    print()
    print("训练后的决策边界 x2 = -(w1*x1 + b)/w2：")
    for x1 in (60.0, 80.0):
        print(f"  面积 {x1:g} 时，边界房龄 x2 = {boundary_x2(weights[0], weights[1], bias, x1):.2f}")
    print("（面积大的样本标签多为 1，边界应把它和高价组分开）")


# ===== 课后作业：三分类 softmax =====
# 示例用 sigmoid 做二分类；作业改成三个类别（低价 0 / 中价 1 / 高价 2），
# 用 softmax 输出三类的概率，并和"三个独立二分类"的输出对比。

import numpy as np

HOMEWORK_ROWS: list[tuple[float, float, int]] = [
    (50.0, 10.0, 0),
    (55.0, 12.0, 0),
    (60.0, 8.0, 0),
    (65.0, 6.0, 1),
    (70.0, 5.0, 1),
    (75.0, 4.0, 1),
    (80.0, 3.0, 2),
    (85.0, 2.0, 2),
    (90.0, 1.0, 2),
]


def design_matrix(rows: list[tuple[float, float, int]]) -> np.ndarray:
    """把 (面积, 房龄) 拼上常数列，返回形状 (样本数, 3) 的设计矩阵。"""
    return np.column_stack(
        [
            np.array([row[0] for row in rows], dtype=float),
            np.array([row[1] for row in rows], dtype=float),
            np.ones(len(rows)),
        ]
    )


def labels_one_hot(rows: list[tuple[float, float, int]], k: int = 3) -> np.ndarray:
    """把每个样本的类别标成 one-hot，返回形状 (样本数, k)。"""
    n = len(rows)
    y = np.zeros((n, k))
    for i, row in enumerate(rows):
        y[i, row[2]] = 1.0
    return y


def softmax(scores: np.ndarray) -> np.ndarray:
    """把每行的分数变成概率，每行和为 1。

    scores 形状 (样本数, 类别数)。返回同形状概率。
    数值上对每行减去该行最大值，避免 exp 溢出（本课数据用不到，写上更稳）。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 softmax")


def softmax_cross_entropy(rows: list[tuple[float, float, int]], weights: np.ndarray) -> float:
    """返回所有样本的平均损失 -log p_c，c 是每行的真实类别。

    weights 形状 (3, 3)：行对应 (面积, 房龄, 常数项)，列对应三个类别。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 softmax_cross_entropy")


def softmax_gradient_step(
    rows: list[tuple[float, float, int]],
    weights: np.ndarray,
    learning_rate: float,
) -> np.ndarray:
    """用平均梯度更新三组权重，返回新 weights。

    梯度：dL/dW = (1/n) * X^T (P - Y)，其中 X 是设计矩阵、Y 是 one-hot 标签。
    learning_rate 必须为正。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 softmax_gradient_step")


def homework() -> None:
    """完成后运行：比较训练前后的损失，并观察 softmax 每行和为 1。"""
    x = design_matrix(HOMEWORK_ROWS)
    y = labels_one_hot(HOMEWORK_ROWS)

    # 和示例一样从全 0 出发，初始损失是 -log(1/3) = log 3 ≈ 1.0986。
    weights = np.zeros((3, 3))
    print(f"初始平均损失：{softmax_cross_entropy(HOMEWORK_ROWS, weights):.4f}")
    print("（应接近 1.0986 = -log(1/3)，三类等概率）")

    # 训练 2000 步。特征尺度和示例相同（面积几十到上百），学习率取小。
    lr = 0.005
    for _ in range(2000):
        weights = softmax_gradient_step(HOMEWORK_ROWS, weights, lr)
    print(f"训练 2000 步后平均损失：{softmax_cross_entropy(HOMEWORK_ROWS, weights):.4f}")

    probs = softmax(x @ weights)
    print("softmax 输出（每行应为三个概率，和为 1）：")
    for i, row in enumerate(probs):
        print(f"  样本 {i}: {np.round(row, 4)}，和 {row.sum():.4f}")

    print("\n对照：若用三个独立二分类，三列各自打分、互不归一化，三数之和")
    print("通常不等于 1；softmax 的每一行由定义保证和为 1。")


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
