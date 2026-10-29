"""第七课示例：朴素贝叶斯的先验、似然、后验，以及拉普拉斯平滑。"""

# ===== 课程示例：房价二分类，离散特征 =====
# 特征：面积（大/小）、房龄（新/旧）；标签：是否高价（1/0）。
# 训练集 10 套房：4 套高价（全部房龄新）、6 套低价。
# 手写朴素贝叶斯：统计先验和各类别内特征概率，再用贝叶斯公式预测。

from collections import Counter

Sample = tuple[str, str, int]
# (面积, 房龄, 是否高价)

ROWS: list[Sample] = [
    ("大", "新", 1),
    ("大", "新", 1),
    ("小", "新", 1),
    ("大", "新", 1),
    ("小", "旧", 0),
    ("小", "旧", 0),
    ("大", "旧", 0),
    ("小", "新", 0),
    ("小", "旧", 0),
    ("大", "新", 0),
]

FEATURE_VALUES = {"面积": ("大", "小"), "房龄": ("新", "旧")}


def fit_naive_bayes(
    rows: list[Sample],
    k: float = 1.0,
) -> dict:
    """统计先验和各类别内每个特征值的概率，返回模型字典。

    模型结构：
        {"classes": [1, 0],                     # 出现的类别，按出现顺序
         "prior": {1: float, 0: float},          # 先验 P(类别)
         "likelihood": {                         # P(特征值 | 类别)
             1: {"面积": {"大": p, "小": p}, "房龄": {"新": p, "旧": p}},
             0: {...},
         }}
    k 是拉普拉斯平滑参数。k=0 不做平滑（某个取值从未出现时概率为 0），
    k>0 时每个取值计数加 k，分母加"取值个数 × k"，保证同特征各取值
    概率之和仍为 1。
    """
    class_counts = Counter(row[2] for row in rows)
    n = len(rows)
    model: dict = {"classes": list(class_counts), "prior": {}, "likelihood": {}}
    for cls in class_counts:
        model["prior"][cls] = class_counts[cls] / n
        cls_rows = [row for row in rows if row[2] == cls]
        per_feature = {}
        for feat_idx, feat_name in enumerate(("面积", "房龄")):
            value_counts = Counter(row[feat_idx] for row in cls_rows)
            denom = len(cls_rows) + k * len(FEATURE_VALUES[feat_name])
            per_feature[feat_name] = {
                value: (value_counts.get(value, 0) + k) / denom
                for value in FEATURE_VALUES[feat_name]
            }
        model["likelihood"][cls] = per_feature
    return model


def predict_naive_bayes(
    model: dict,
    sample: tuple[str, str],
    class_names: list[int],
) -> dict[int, float]:
    """对一条样本返回每个类别的后验概率，和为 1。

    sample 是 (面积, 房龄)。先对每个类别算 先验 × 各特征似然 的乘积，
    再统一除以所有类别的和（相当于公式里的 P(x)），归一化得到后验。
    """
    scores = {}
    for cls in model["classes"]:
        score = model["prior"][cls]
        for feat_idx, feat_name in enumerate(("面积", "房龄")):
            value = sample[feat_idx]
            score *= model["likelihood"][cls][feat_name][value]
        scores[cls] = score
    total = sum(scores.values())
    return {cls: scores[cls] / total for cls in class_names}


def show_model(model: dict) -> None:
    """打印先验和各类别特征概率，便于对照手算。"""
    for cls in model["classes"]:
        prior = model["prior"][cls]
        name = "高价" if cls == 1 else "低价"
        print(f"类别 {name}：先验 P = {prior:.3f}")
        for feat, probs in model["likelihood"][cls].items():
            parts = ", ".join(f"{v}={p:.3f}" for v, p in probs.items())
            print(f"  P({feat} | {name})：{parts}")


def main() -> None:
    print("=== 训练数据：10 套房 ===")
    print("高价 4 套（全部房龄新），低价 6 套。")
    print()

    print("先验：")
    counts = Counter(row[2] for row in ROWS)
    print(f"  P(高价) = {counts[1]}/{len(ROWS)} = 0.4")
    print(f"  P(低价) = {counts[0]}/{len(ROWS)} = 0.6")
    print()

    print("新房：面积小、房龄旧。")
    for k, label in ((0.0, "无平滑 k=0"), (1.0, "拉普拉斯平滑 k=1")):
        model = fit_naive_bayes(ROWS, k=k)
        posterior = predict_naive_bayes(model, ("小", "旧"), [1, 0])
        print(f"{label}：P(高价|小,旧) = {posterior[1]:.4f}，"
              f"P(低价|小,旧) = {posterior[0]:.4f}")
    print()
    print("注意 k=0 时高价后验为 0：'房龄旧'从未在高价里出现，"
          "一个特征值一票否决。")
    print("k=1 后非零：平滑只说明'没见过不等于不可能'，结论仍由全部证据决定。")
    print()

    print("=== k=1 时各类别的先验和特征概率（对照第 3、4 节手算） ===")
    show_model(fit_naive_bayes(ROWS, k=1.0))


# ===== 课后作业：垃圾邮件二分类 =====
# 示例是房价；作业换成垃圾邮件：特征是"含'优惠'"和"含'发票'"（0/1），
# 标签是"是否垃圾邮件"。要求实现 fit/predict，并对比 k=0 和 k=1。

MailSample = tuple[int, int, int]
# (含优惠, 含发票, 是否垃圾)

MAIL_ROWS: list[MailSample] = [
    (1, 1, 1),   # 垃圾：含优惠、含发票
    (1, 0, 1),   # 垃圾：只含优惠
    (1, 1, 1),   # 垃圾
    (0, 0, 1),   # 垃圾：两个词都不含（噪声样本）
    (1, 0, 1),   # 垃圾：只含优惠
    (0, 0, 0),   # 正常
    (0, 1, 0),   # 正常：含发票（可能是账单）
    (0, 0, 0),   # 正常
]

MAIL_FEATURE_VALUES = {"含优惠": (1, 0), "含发票": (1, 0)}


def fit_mail_naive_bayes(
    rows: list[MailSample],
    k: float = 1.0,
) -> dict:
    """输入 (含优惠, 含发票, 是否垃圾)，返回和示例 fit_naive_bayes 同结构的模型。

    特征名固定为 "含优惠" 和 "含发票"，取值 1/0。k 是拉普拉斯平滑参数。
    """
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 fit_mail_naive_bayes")


def predict_mail(
    model: dict,
    sample: tuple[int, int],
) -> dict[int, float]:
    """对一条 (含优惠, 含发票) 样本返回 {1: 垃圾概率, 0: 正常概率}，和为 1。"""
    # TODO 作业：完成这个函数
    raise NotImplementedError("请完成 predict_mail")


def homework() -> None:
    """完成后运行：对比 k=0 和 k=1 下新邮件的后验。"""
    new_mail = (1, 1)   # 含优惠、含发票
    print("新邮件：含'优惠'、含'发票'")
    for k, label in ((0.0, "无平滑 k=0"), (1.0, "拉普拉斯平滑 k=1")):
        model = fit_mail_naive_bayes(MAIL_ROWS, k=k)
        posterior = predict_mail(model, new_mail)
        print(f"{label}：P(垃圾|优惠,发票) = {posterior[1]:.4f}，"
              f"P(正常|优惠,发票) = {posterior[0]:.4f}")


if __name__ == "__main__":
    main()
    # 完成作业函数后，取消下一行注释再运行。
    # homework()
