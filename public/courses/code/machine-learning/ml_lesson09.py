"""第九课示例：单棵树 vs 随机森林 vs GBDT，以及重采样对方差的影响。"""

# ===== 课程示例：圆形边界的分类对照 =====
# 数据：x1, x2 在 [-3,3]，真实边界 x1^2 + x2^2 < 4（圆形），
# 翻转 15% 的标签制造噪声。
# 对照：单棵决策树（过拟合）、随机森林（降方差）、GBDT（Boosting）。

import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split


def make_circle_data(
    n: int = 300,
    noise: float = 0.15,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """生成圆形边界分类数据：x1^2 + x2^2 < 4 判为正类，加标签噪声。

    noise 是标签翻转比例：这个比例的数据点把 0 翻成 1 或反过来。
    返回 (特征, 标签)。噪声让过拟合和方差问题真实可观察。
    """
    rng = np.random.default_rng(seed)
    x1 = rng.uniform(-3.0, 3.0, n)
    x2 = rng.uniform(-3.0, 3.0, n)
    y = ((x1**2 + x2**2) < 4.0).astype(int)
    flip = rng.random(n) < noise
    y[flip] = 1 - y[flip]
    return np.column_stack([x1, x2]), y


def evaluate_models(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[float, float, float]:
    """训练单棵树、随机森林、GBDT，返回三个模型的测试准确率。

    内部做一次 70/30 训练测试切分（random_state=0 固定，结果可复现）。
    """
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.3, random_state=0
    )

    tree = DecisionTreeClassifier(random_state=0)
    tree.fit(x_train, y_train)
    tree_acc = tree.score(x_test, y_test)

    rf = RandomForestClassifier(n_estimators=50, random_state=0)
    rf.fit(x_train, y_train)
    rf_acc = rf.score(x_test, y_test)

    gb = GradientBoostingClassifier(n_estimators=50, random_state=0)
    gb.fit(x_train, y_train)
    gb_acc = gb.score(x_test, y_test)

    return tree_acc, rf_acc, gb_acc


def bootstrap_disagreement(
    x_train: np.ndarray,
    y_train: np.ndarray,
    x_test: np.ndarray,
    model_factory,
    rounds: int = 30,
) -> float:
    """对训练集做 rounds 次有放回重采样，返回模型预测的分歧率。

    每次重采样训练一个新模型，记录它在 x_test 上的预测；分歧率是
    "某次预测与 30 次投票结果不同"的样本占比。分歧率越大说明模型对
    训练样本越敏感（方差越大）。model_factory 接受随机种子返回新模型。
    """
    rng = np.random.default_rng(0)
    preds = []
    for seed in range(rounds):
        idx = rng.choice(len(x_train), len(x_train), replace=True)
        model = model_factory(seed)
        model.fit(x_train[idx], y_train[idx])
        preds.append(model.predict(x_test))
    preds = np.array(preds)  # 形状 (rounds, 测试样本数)
    mode = np.apply_along_axis(
        lambda row: np.bincount(row).argmax(), 0, preds
    )
    return float(np.mean(preds != mode))


def main() -> None:
    x, y = make_circle_data()

    print("=== 圆形边界 + 15% 标签噪声 ===")
    print(f"样本数 {len(y)}，正类比例 {y.mean():.2f}")
    print()

    tree_acc, rf_acc, gb_acc = evaluate_models(x, y)
    print("测试准确率：")
    print(f"  单棵决策树：{tree_acc:.3f}（过拟合：训练接近 1，测试低）")
    print(f"  随机森林 50 棵：{rf_acc:.3f}（Bagging 降方差）")
    print(f"  GBDT 50 轮：{gb_acc:.3f}（Boosting，噪声下略低于随机森林）")
    print()

    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=0.3, random_state=0
    )
    tree_dis = bootstrap_disagreement(
        x_train, y_train, x_test,
        lambda s: DecisionTreeClassifier(random_state=s),
    )
    rf_dis = bootstrap_disagreement(
        x_train, y_train, x_test,
        lambda s: RandomForestClassifier(n_estimators=50, random_state=s),
    )
    print("bootstrap 30 次的预测分歧率（越大越敏感、方差越大）：")
    print(f"  单棵决策树：{tree_dis:.4f}")
    print(f"  随机森林：{rf_dis:.4f}")
    print("随机森林把多棵树的波动平均掉，分歧率约为单树一半。")
    print()

    # 单棵树结构随 bootstrap 扰动漂移的直接证据
    print("同一份数据做 bootstrap 扰动，单棵树根节点分裂的变化：")
    rng = np.random.default_rng(0)
    for seed in range(4):
        idx = rng.choice(len(x_train), len(x_train), replace=True)
        tree = DecisionTreeClassifier(random_state=seed)
        tree.fit(x_train[idx], y_train[idx])
        feat = tree.tree_.feature[0]
        thr = tree.tree_.threshold[0]
        name = "x1" if feat == 0 else "x2"
        print(f"  seed={seed}：根分裂 {name} ≤ {thr:.2f}")


# ===== 课后作业：棋盘边界 + 噪声对比 =====
# 示例是圆形边界；作业改成棋盘状边界（更难的决策面），
# 并对比随机森林和 GBDT 在低噪声/高噪声下的表现。

def make_checkerboard_data(
    n: int = 400,
    noise: float = 0.05,
    seed: int = 0,
) -> tuple[np.ndarray, np.ndarray]:
    """生成棋盘状分类数据。

    x1, x2 均匀取自 [0, 4)。标签由 "int(x1) + int(x2) 的奇偶" 决定：
    和为偶数 -> 0，和为奇数 -> 1。noise 是标签翻转比例。
    返回 (特征, 标签)。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 make_checkerboard_data")


def evaluate_models_checker(
    x: np.ndarray,
    y: np.ndarray,
) -> tuple[float, float, float]:
    """训练单棵树、随机森林、GBDT，返回 (tree, rf, gb) 三个测试准确率。

    切分固定 random_state=0；三个模型的 n_estimators 都取 50。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 evaluate_models_checker")


def homework() -> None:
    """完成后运行：对比低噪声和高噪声下三个模型的表现。"""
    for noise, label in ((0.05, "低噪声 5%"), (0.3, "高噪声 30%")):
        x, y = make_checkerboard_data(noise=noise)
        tree_acc, rf_acc, gb_acc = evaluate_models_checker(x, y)
        print(f"{label}：单树 {tree_acc:.3f}，随机森林 {rf_acc:.3f}，GBDT {gb_acc:.3f}")
    print("预期：噪声低时 GBDT 可能超过随机森林（补偏差）；噪声高时随机森林更稳。")


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
