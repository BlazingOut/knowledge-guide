"""第五课示例：过拟合/欠拟合对照，以及 L1/L2 正则的效果。"""

# ===== 课程示例：多项式特征下的泛化与正则 =====
# 真实关系是 y = 3x^2 + 2x + 1 再加一点噪声。x 是唯一的输入。
# 候选模型用 x 的一次、二次、十五次幂做特征：
#   一次   -> 表达不了弯曲，欠拟合
#   二次   -> 正好是真实形状，合适
#   十五次 -> 连噪声一起记住，过拟合
# 然后用 Ridge（L2）和 Lasso（L1）对十五次特征加正则，看误差回落。

import numpy as np
from sklearn.linear_model import LinearRegression, Ridge, Lasso

# 固定随机种子，保证每次运行结果一致，方便对照文档。
rng = np.random.default_rng(0)
N_TRAIN, N_TEST = 15, 200


def true_price(x: np.ndarray) -> np.ndarray:
    """本课使用的真实关系：二次曲线加常数。"""
    return 3.0 * x**2 + 2.0 * x + 1.0


def make_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """独立生成训练集和测试集，同分布：都在 (0,1) 上采样，再加同幅度的噪声。

    返回 (x_train, y_train, x_test, y_test)。x 是面积之类的数值输入，
    标签是成交价之类的连续值。噪声幅度 0.3 固定，所以二次模型的最好
    测试误差接近 0.3^2 = 0.09。
    """
    x_train = rng.uniform(0.05, 0.95, N_TRAIN)
    x_test = rng.uniform(0.05, 0.95, N_TEST)
    noise_train = rng.normal(0.0, 0.3, N_TRAIN)
    noise_test = rng.normal(0.0, 0.3, N_TEST)
    return x_train, true_price(x_train) + noise_train, x_test, true_price(x_test) + noise_test


def polynomial_features(x: np.ndarray, degree: int) -> np.ndarray:
    """把一列输入展开成 [x, x^2, ..., x^degree]，返回形状 (样本数, degree)。

    不包含常数项：sklearn 的回归器会自己加 intercept_。
    x 的取值范围要在 1 以内，否则高次幂会放大到无法计算（本课数据在 (0,1)）。
    """
    return np.column_stack([x**k for k in range(1, degree + 1)])


def mean_squared_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """平均平方误差，与第 3 课的指标一致。"""
    return float(np.mean((y_true - y_pred) ** 2))


def fit_and_report(
    label: str,
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    y_test: np.ndarray,
    model,
) -> None:
    """拟合一个 sklearn 回归器，打印训练和测试误差。

    model 是已经构造好的回归器对象（如 LinearRegression()）。
    fit 在训练集上学习参数，predict 在两个集合上预测，误差分开报告。
    """
    model.fit(x_train, y_train)
    train_mse = mean_squared_error(y_train, model.predict(x_train))
    test_mse = mean_squared_error(y_test, model.predict(x_test))
    print(f"  {label:22s} 训练误差 {train_mse:.4f}  测试误差 {test_mse:.4f}")


def main() -> None:
    x_train, y_train, x_test, y_test = make_data()

    print("三种特征复杂度的对照（噪声方差 0.09，二次模型测试误差应接近它）：")
    for degree, label in ((1, "一次"), (2, "二次"), (15, "十五次")):
        x_tr = polynomial_features(x_train, degree)
        x_te = polynomial_features(x_test, degree)
        fit_and_report(label, x_tr, y_train, x_te, y_test, LinearRegression())
    print()

    x_tr = polynomial_features(x_train, 15)
    x_te = polynomial_features(x_test, 15)
    print("对十五次特征加正则，测试误差应明显回落：")
    for alpha in (0.05, 0.1, 0.5):
        ridge = Ridge(alpha=alpha)
        fit_and_report(f"Ridge alpha={alpha}", x_tr, y_train, x_te, y_test, ridge)
        nonzero = int(np.sum(np.abs(ridge.coef_) > 1e-8))
        print(f"       （L2 收缩：15 个系数保留 {nonzero} 个，通常全保留）")
    print()

    print("L1 正则（Lasso）会把一部分系数压成 0：")
    for alpha in (0.01, 0.05, 0.1):
        lasso = Lasso(alpha=alpha, max_iter=100000)
        fit_and_report(f"Lasso alpha={alpha}", x_tr, y_train, x_te, y_test, lasso)
        zero = int(np.sum(np.abs(lasso.coef_) < 1e-8))
        print(f"       （L1 稀疏：15 个系数中有 {zero} 个为 0）")


# ===== 课后作业：K 折交叉验证选 alpha =====
# 示例用固定的 alpha 演示正则效果；作业改成在验证集上选 alpha：
# 把训练集切成 k 折，轮流留 1 折验证，对每个 alpha 求出平均验证误差，
# 选最小者，再用它报告测试误差。这样选出的 alpha 没有偷看测试集。

def k_fold_mse(
    features: np.ndarray,
    labels: np.ndarray,
    alpha_list: list[float],
    k: int = 5,
) -> list[float]:
    """对每个 alpha 返回 k 折平均验证误差，列表顺序与 alpha_list 一致。

    features 形状 (样本数, 特征数)，labels 形状 (样本数,)。
    把样本按顺序切成长度接近的 k 份，轮流留 1 份验证、其余 k-1 份训练，
    每次用 Ridge(alpha=alpha) 拟合，验证份上算平均平方误差，最后取平均。
    k 必须至少是 2，且不超过样本数。不修改输入数组。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 k_fold_mse")


def best_alpha(alpha_list: list[float], cv_errors: list[float]) -> float:
    """返回平均验证误差最小的 alpha。两个列表长度必须相同。"""
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 best_alpha")


def homework() -> None:
    """完成后运行：打印每个 alpha 的验证误差、选出的最优 alpha 和测试误差。"""
    x_train, y_train, x_test, y_test = make_data()
    x_tr = polynomial_features(x_train, 15)
    x_te = polynomial_features(x_test, 15)

    alpha_list = [0.01, 0.05, 0.1, 0.5, 1.0]
    cv_errors = k_fold_mse(x_tr, y_train, alpha_list, k=5)
    print("各 alpha 的 5 折平均验证误差：")
    for alpha, err in zip(alpha_list, cv_errors):
        print(f"  alpha={alpha}: {err:.4f}")

    chosen = best_alpha(alpha_list, cv_errors)
    print(f"最优 alpha = {chosen}")

    ridge = Ridge(alpha=chosen).fit(x_tr, y_train)
    test_mse = mean_squared_error(y_test, ridge.predict(x_te))
    print(f"用最优 alpha 在完整训练集上拟合，测试误差 {test_mse:.4f}")

    lasso = Lasso(alpha=chosen, max_iter=100000).fit(x_tr, y_train)
    zero = int(np.sum(np.abs(lasso.coef_) < 1e-8))
    print(f"同一 alpha 下 Lasso 的系数中，有 {zero} 个为 0（L1 稀疏）")


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
