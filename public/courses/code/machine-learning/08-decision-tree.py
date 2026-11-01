"""第八课示例：决策树分裂准则手算，以及 sklearn 决策树在连续特征上的表现。"""

# ===== 课程示例一：8 条样本的手算分裂准则 =====
# 特征：房龄（新/旧）、楼层（高/低）；标签：是否成交（1/0）。
# 手算信息熵、按房龄/楼层分裂的信息增益和基尼系数，与正文第 2 节对照。

import math
from collections import defaultdict

import numpy as np
from sklearn.tree import DecisionTreeClassifier


def entropy(labels: list[int]) -> float:
    """一组标签的信息熵 -Σ p_k log2 p_k。全同类别或为空时返回 0。"""
    if not labels:
        return 0.0
    counts = defaultdict(int)
    for label in labels:
        counts[label] += 1
    total = len(labels)
    result = 0.0
    for count in counts.values():
        p = count / total
        result -= p * math.log2(p)
    return result


def gini(labels: list[int]) -> float:
    """一组标签的基尼系数 1 - Σ p_k^2。全同类别或为空时返回 0。"""
    if not labels:
        return 0.0
    counts = defaultdict(int)
    for label in labels:
        counts[label] += 1
    total = len(labels)
    result = 1.0
    for count in counts.values():
        p = count / total
        result -= p * p
    return result


def split_purity(
    samples: list[tuple[str, str, int]],
    feature_idx: int,
    criterion: str,
) -> float:
    """按第 feature_idx 个特征分裂后，两支纯度的加权平均。

    criterion 为 "entropy" 时算熵（越小越纯），为 "gini" 时算基尼（越小越纯）。
    返回的是分裂后各支纯度的加权平均，越小表示分裂后整体越纯。
    """
    groups: dict[str, list[int]] = defaultdict(list)
    for sample in samples:
        groups[sample[feature_idx]].append(sample[2])
    total = len(samples)
    weighted = 0.0
    for labels in groups.values():
        if criterion == "entropy":
            impurity = entropy(labels)
        else:
            impurity = gini(labels)
        weighted += (len(labels) / total) * impurity
    return weighted


def main() -> None:
    samples: list[tuple[str, str, int]] = [
        ("新", "高", 1),
        ("新", "高", 1),
        ("新", "低", 1),
        ("新", "低", 1),
        ("旧", "高", 0),
        ("旧", "高", 0),
        ("旧", "低", 0),
        ("旧", "低", 1),
    ]
    labels = [sample[2] for sample in samples]

    print("=== 手算分裂准则（8 条样本） ===")
    print(f"分裂前标签：5 成交、3 不成交")
    h_before = entropy(labels)
    print(f"分裂前信息熵 H(y) = {h_before:.4f}")
    print()

    for name, idx in (("房龄", 0), ("楼层", 1)):
        h_after = split_purity(samples, idx, "entropy")
        g_after = split_purity(samples, idx, "gini")
        gain = h_before - h_after
        print(f"按{name}分裂：信息增益 = {h_before:.4f} - {h_after:.4f} = {gain:.4f}")
        print(f"          基尼（加权） = {g_after:.4f}")
    print("信息增益越大越好，基尼越小越好；两个准则都选中'房龄'。")
    print()

    print("=== sklearn 决策树：连续特征（面积、房龄） ===")
    rng = np.random.default_rng(0)
    n = 40
    x_area = rng.uniform(30.0, 120.0, n)
    x_age = rng.uniform(1.0, 20.0, n)
    # 真实规则：面积 > 70 且 房龄 < 12 才成交。
    y = ((x_area > 70.0) & (x_age < 12.0)).astype(int)
    x = np.column_stack([x_area, x_age])
    print(f"正类（成交）比例：{y.mean():.2f}")

    model = DecisionTreeClassifier(max_depth=2, random_state=0)
    model.fit(x, y)
    print(f"训练准确率：{model.score(x, y):.3f}")
    print(f"节点数：{model.tree_.node_count}")
    print(f"各节点分裂特征（0=面积，1=房龄，-2=叶子）：{model.tree_.feature}")
    print(f"各节点分裂阈值：{np.round(model.tree_.threshold, 2)}")
    print(f"特征重要性：{np.round(model.feature_importances_, 3)}")
    print("第一层选'房龄'阈值 11.94，第二层选'面积'阈值 72.66，")
    print("与真实规则'面积 > 70 且 房龄 < 12'吻合。")
    print()

    print("=== 深度与过拟合 ===")
    for depth in (1, 3, 10):
        deep = DecisionTreeClassifier(max_depth=depth, random_state=0)
        deep.fit(x, y)
        print(f"max_depth={depth:2d}：训练准确率 {deep.score(x, y):.3f}")
    print("深度越大训练准确率越高（越能记住训练数据），真实数据上验证误差会回升。")


# ===== 课后作业：三分类的两种准则 + 深度对比 =====
# 示例是二分类；作业改成三分类（成交 2 / 观望 1 / 不成交 0），
# 要求手写分裂准则函数，并观察深度对训练误差的影响。

SAMPLE_12: list[tuple[int, int, int]] = [
    # (面积档 0/1, 楼层档 0/1, 标签 0/1/2)
    (0, 0, 0), (0, 0, 0), (0, 1, 0), (0, 1, 1),
    (1, 0, 1), (1, 0, 1), (1, 1, 2), (1, 1, 2),
    (0, 0, 1), (1, 0, 2), (0, 1, 1), (1, 1, 2),
]


def best_split(
    samples: list[tuple[int, int, int]],
    criterion: str,
) -> tuple[int, float]:
    """对每个特征每个取值尝试二分，返回 (最佳特征下标, 分裂后总纯度)。

    criterion 是 "entropy" 或 "gini"。总纯度是两支纯度的加权平均，越小越好。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 best_split")


def homework() -> None:
    """完成后运行：两个准则选出的特征应一致；再看深度的过拟合效应。"""
    for criterion in ("entropy", "gini"):
        best_feat, impurity = best_split(SAMPLE_12, criterion)
        names = {0: "面积档", 1: "楼层档"}
        print(f"准则 {criterion}：最佳分裂特征 = {names[best_feat]}，总纯度 = {impurity:.4f}")
    print("（两个准则应选中同一个特征）")
    print()

    rng = np.random.default_rng(1)
    n = 60
    x_area = rng.uniform(30.0, 120.0, n)
    x_age = rng.uniform(1.0, 20.0, n)
    y = ((x_area > 70.0) & (x_age < 12.0)).astype(int)
    x = np.column_stack([x_area, x_age])
    for depth in (1, 2, 5, 20):
        model = DecisionTreeClassifier(max_depth=depth, random_state=0)
        model.fit(x, y)
        print(f"max_depth={depth:2d}：训练准确率 {model.score(x, y):.3f}")


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
