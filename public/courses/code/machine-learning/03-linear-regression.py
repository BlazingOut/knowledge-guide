"""第三课示例：线性回归的正规方程，以及用梯度下降走两步。"""

# ===== 课程示例：面积、房龄和常数项 =====
# 三条样本正好落在 ŷ = 3*面积 + 2*房龄 + 10 上，
# 用来把正规方程的结果和手算对照。只有两条时，三个参数没有唯一解。
# 梯度下降从 0 出发，只走两步，损失会下降，但不应指望两步就到达 [3, 2, 10]。

import numpy as np


def design_matrix(areas: np.ndarray, ages: np.ndarray) -> np.ndarray:
    """把面积、房龄和一列 1 拼成形状 (样本数, 3) 的设计矩阵。"""
    ones = np.ones(len(areas))
    return np.column_stack([areas, ages, ones])


def predict(features: np.ndarray, weights: np.ndarray) -> np.ndarray:
    """ŷ = X w。features 已包含常数列。"""
    return features @ weights


def normal_equation(features: np.ndarray, labels: np.ndarray) -> np.ndarray:
    """返回使均方误差最小的参数向量，解 (X^T X) w = X^T y。

    features 形状 (样本数, 参数个数)，labels 形状 (样本数,)。
    返回形状 (参数个数,)。不修改输入。
    列之间可互相线性表示时，X^T X 不可逆，np.linalg.solve 会失败。
    """
    gram = features.T @ features
    right_hand = features.T @ labels
    return np.linalg.solve(gram, right_hand)


def mean_squared_error(features: np.ndarray, labels: np.ndarray, weights: np.ndarray) -> float:
    """平均平方误差。样本数为 0 时抛出 ValueError。"""
    if len(labels) == 0:
        raise ValueError("至少需要一条样本")
    gap = labels - predict(features, weights)
    return float(np.mean(gap * gap))


def gradient_step(
    features: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
    learning_rate: float,
) -> np.ndarray:
    """用全部样本的平均梯度走一步，返回新参数。不修改 weights。

    每个参数的平均梯度是 -2/n * Σ (y - ŷ) * 对应特征列。
    """
    if learning_rate <= 0:
        raise ValueError("learning_rate 必须为正")
    residual = labels - predict(features, weights)
    gradient = -2.0 / len(labels) * (features.T @ residual)
    return weights - learning_rate * gradient


def main() -> None:
    areas = np.array([50.0, 80.0, 60.0])
    ages = np.array([10.0, 4.0, 6.0])
    labels = np.array([180.0, 258.0, 202.0])
    features = design_matrix(areas, ages)

    solved = normal_equation(features, labels)
    print("正规方程的参数 [面积系数, 房龄系数, 常数项]：")
    print(" ", np.round(solved, decimals=6))
    print("三条残差：", np.round(labels - predict(features, solved), decimals=6))
    print()

    weights = np.zeros(3)
    first_residual = labels[0] - predict(features, weights)[0]
    area_gradient = -2.0 * first_residual * features[0, 0]
    print(f"权重全 0 时，第一条样本对面积系数的梯度：{area_gradient}")
    print(f"初始平均损失：{mean_squared_error(features, labels, weights):.1f}")
    for step in (1, 2):
        weights = gradient_step(features, labels, weights, learning_rate=1e-5)
        loss = mean_squared_error(features, labels, weights)
        print(f"第 {step} 步之后的损失：{loss:.1f}，参数 {np.round(weights, decimals=4)}")


# ===== 课后作业：三套房子的残差，以及删掉重复列 =====
# 示例的两个点可以完全拟合。作业的三个点用来看残差，
# 并在房龄列变成面积的倍数时停下来，不要对不可逆矩阵求逆。

THREE_AREAS = np.array([40.0, 60.0, 90.0])
THREE_AGES = np.array([12.0, 8.0, 5.0])
THREE_PRICES = np.array([160.0, 210.0, 250.0])


def residuals(
    features: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
) -> np.ndarray:
    """返回每条样本的 y - ŷ，形状与 labels 相同。"""
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 residuals")


def drop_duplicate_column(features: np.ndarray) -> np.ndarray:
    """若某个原始特征列正好是另一列的常数倍，删掉列号较大的那一列。

    最后一列是常数项，不参与比较，也必须保留。
    没有重复列时返回拷贝。只删除一对中列号较大的一列；
    本课数据里最多只会有一列需要删除。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 drop_duplicate_column")


def homework() -> None:
    """完成后运行：三套房子应解出一组系数，且残差不会全是 0。"""
    features = design_matrix(THREE_AREAS, THREE_AGES)
    weights = normal_equation(features, THREE_PRICES)
    print("三个系数：", np.round(weights, decimals=4))
    print("三条残差：", np.round(residuals(features, THREE_PRICES, weights), decimals=4))

    duplicated = np.column_stack([THREE_AREAS, THREE_AREAS * 2.0, np.ones(3)])
    reduced = drop_duplicate_column(duplicated)
    print("删掉重复列之后的形状：", reduced.shape)
    print(reduced)


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
