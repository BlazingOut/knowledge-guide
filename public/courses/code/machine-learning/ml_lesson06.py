"""第六课示例：分类指标（准确率/精确率/召回率/F1/AUC）和回归指标（MAE/MSE）。"""

# ===== 课程示例：20 套房子的固定预测 =====
# 真实标签：3 套高价（正类 1）、17 套低价（负类 0），类别不均衡。
# 模型预测分数是预先给定的（本课只评估预测，不训练模型）：
#   3 个正类中 2 个分数高、1 个低；17 个负类中 3 个分数高（误报）、14 个低。
# 阈值取 0.5：分数 >= 0.5 预测为正类。

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    roc_curve,
    precision_recall_curve,
    auc,
    mean_absolute_error,
    mean_squared_error,
)

Y_TRUE = np.array([1, 1, 1] + [0] * 17)
# 前 3 个是高价，后 17 个是低价。

SCORES = np.array([
    0.9, 0.7, 0.3,          # 3 个正类：第 3 个漏报
    0.8, 0.6, 0.55, 0.45,   # 负类：前 3 个误报（>=0.5）
    0.4, 0.35, 0.25, 0.2, 0.15, 0.12, 0.1, 0.08, 0.06, 0.05, 0.04, 0.03, 0.02,
])


def threshold_predict(scores: np.ndarray, threshold: float = 0.5) -> np.ndarray:
    """分数 >= threshold 预测为正类，返回 0/1 数组。"""
    return (scores >= threshold).astype(int)


def confusion_counts(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[int, int, int, int]:
    """返回 (TP, FP, FN, TN)，顺序与第 2 节混淆矩阵一致。

    TP：真为 1 且预测 1；FP：真为 0 但预测 1；
    FN：真为 1 但预测 0；TN：真为 0 且预测 0。
    """
    tp = int(np.sum((y_true == 1) & (y_pred == 1)))
    fp = int(np.sum((y_true == 0) & (y_pred == 1)))
    fn = int(np.sum((y_true == 1) & (y_pred == 0)))
    tn = int(np.sum((y_true == 0) & (y_pred == 0)))
    return tp, fp, fn, tn


def show_classification(y_true: np.ndarray, y_pred: np.ndarray, label: str) -> None:
    """打印一组预测的四格和四个分类指标。"""
    tp, fp, fn, tn = confusion_counts(y_true, y_pred)
    acc = accuracy_score(y_true, y_pred)
    prec = precision_score(y_true, y_pred)
    rec = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)
    print(f"{label}：")
    print(f"  四格 TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"  准确率 {acc:.4f}  精确率 {prec:.4f}  召回率 {rec:.4f}  F1 {f1:.4f}")


def main() -> None:
    print("=== 分类指标 ===")
    print(f"真实标签：3 个高价（正类）、17 个低价（负类），负类占 {Y_TRUE.size - 3}/{Y_TRUE.size}")

    y_pred = threshold_predict(SCORES, 0.5)
    show_classification(Y_TRUE, y_pred, "阈值 0.5 的预测")

    all_neg = np.zeros_like(Y_TRUE)
    show_classification(Y_TRUE, all_neg, "全部预测为低价")
    print("  -> 全预测多数类准确率反而更高，精确率/召回率为 0：准确率被多数类刷高。")
    print()

    auc_value = roc_auc_score(Y_TRUE, SCORES)
    print(f"AUC（sklearn）：{auc_value:.4f}")

    # 手算 AUC：正类分数 > 负类分数的对数占比
    pos = SCORES[Y_TRUE == 1]
    neg = SCORES[Y_TRUE == 0]
    pairs = 0
    total = 0
    for p in pos:
        for n in neg:
            total += 1
            if p > n:
                pairs += 1
            elif p == n:
                pairs += 0.5
    print(f"AUC（手算 3×17={total} 对）：{pairs / total:.4f}，与 sklearn 一致。")
    print()

    fpr, tpr, _ = roc_curve(Y_TRUE, SCORES)
    precision, recall, _ = precision_recall_curve(Y_TRUE, SCORES)
    print(f"PR 曲线下面积（PR-AUC）：{auc(recall, precision):.4f}")
    print(f"PR 基准线 = 正类比例 {Y_TRUE.mean():.4f}，PR-AUC 要跟它比，不是跟 0.5 比。")
    print()

    print("=== 回归指标 ===")
    y_price = np.array([200.0, 258.0, 202.0, 310.0, 180.0])
    y_pred_price = np.array([208.0, 250.0, 215.0, 285.0, 185.0])
    mae = mean_absolute_error(y_price, y_pred_price)
    mse = mean_squared_error(y_price, y_pred_price)
    print(f"5 套房子的真实价和预测价：")
    for real, pred in zip(y_price, y_pred_price):
        print(f"  真实 {real:6.1f}  预测 {pred:6.1f}  差 {pred - real:6.1f}")
    print(f"MAE = {mae:.4f}（平均每套偏差，单位万元）")
    print(f"MSE = {mse:.4f}（平方后取平均，大误差被放大）")


# ===== 课后作业：100 笔交易中 5 笔欺诈 =====
# 场景换成欺诈检测：5 个欺诈（正类）、95 个正常（负类）。
# 预测分数给定。要求手写四个指标，再和 sklearn 对照；最后全判"非欺诈"。

FRAUD_Y = np.array([1] * 5 + [0] * 95)

FRAUD_SCORES = np.array([
    # 5 个欺诈的分数：4 个高、1 个低（漏报）
    0.95, 0.88, 0.82, 0.75, 0.30,
    # 3 个正常但分数高的（误报）
    0.90, 0.70, 0.55,
    # 92 个正常的低分：前 20 个逐渐降低，后面 72 个都是 0
    0.48, 0.45, 0.40, 0.35, 0.28, 0.25, 0.22, 0.20, 0.18, 0.15,
    0.12, 0.10, 0.08, 0.07, 0.06, 0.05, 0.04, 0.03, 0.02, 0.01,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
])


def my_precision_recall_f1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """从四格手工算精确率、召回率、F1。分母为 0 时返回 0。"""
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 my_precision_recall_f1")


def my_accuracy(tp: int, fp: int, fn: int, tn: int) -> float:
    """从四格手工算准确率 (TP+TN)/(TP+FP+FN+TN)。"""
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 my_accuracy")


def homework() -> None:
    """完成后运行：手写指标与 sklearn 对照，再看全判非欺诈。"""
    y_pred = threshold_predict(FRAUD_SCORES, 0.5)
    tp, fp, fn, tn = confusion_counts(FRAUD_Y, y_pred)

    my_prec, my_rec, my_f1 = my_precision_recall_f1(tp, fp, fn)
    my_acc = my_accuracy(tp, fp, fn, tn)

    print("手写指标：")
    print(f"  精确率 {my_prec:.4f}  召回率 {my_rec:.4f}  F1 {my_f1:.4f}  准确率 {my_acc:.4f}")
    print("sklearn 对照：")
    print(
        f"  精确率 {precision_score(FRAUD_Y, y_pred):.4f}  "
        f"召回率 {recall_score(FRAUD_Y, y_pred):.4f}  "
        f"F1 {f1_score(FRAUD_Y, y_pred):.4f}  "
        f"准确率 {accuracy_score(FRAUD_Y, y_pred):.4f}"
    )
    print()

    all_neg = np.zeros_like(FRAUD_Y)
    print("全部预测为'非欺诈'：")
    print(
        f"  准确率 {accuracy_score(FRAUD_Y, all_neg):.4f}  "
        f"精确率 {precision_score(FRAUD_Y, all_neg):.4f}  "
        f"召回率 {recall_score(FRAUD_Y, all_neg):.4f}"
    )


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
