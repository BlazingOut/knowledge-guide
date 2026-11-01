# -*- coding: utf-8 -*-
"""第 6 课综合练习：把一条车货请求从硬过滤跑到精确率（不使用任何机器学习库）。

场景：一笔货（北京 -> 天津，9.6 米厢式，明早装货）进入系统，
系统为它从 7 名司机里排出名单。八步链路中本代码覆盖第 2~7 步：
硬过滤 -> 两路召回合并去重 -> 特征表 -> 规则打分 -> 重排 -> 精确率。

只用字典、列表、集合和 sorted，不引入任何机器学习库。
打分公式是固定权重，不是训练出来的——它演示的是推理与评估的形状（第 3 课）。

运行：python code/search-recommend/search_recommend_lesson06.py
"""

# 货源信息：一笔待匹配的货。报价会与每名司机的历史均价比较，得出价格偏离。
QUERY = {
    "出发地": "北京",
    "目的地": "天津",
    "车型": "9.6米厢式",
    "装货时段": "明早",
    "报价": 1250,
}

# 该线路的历史成交均价，用于价格偏离特征。第 4 课：偏离是打分前能查到的特征。
LANE_AVG_PRICE = {"北京-天津": 1180}

# 司机池。后来成交是事后才记录的标签（第 3 课），推理时不能用。
DRIVERS = [
    {"id": "D1", "姓名": "张师傅", "车队": "顺达", "车型": "9.6米厢式", "城市": "北京",
     "常跑线路": {"北京-天津", "北京-廊坊"}, "历史成交": 22, "均价": 1180,
     "新司机": False, "浏览过本线路": True, "后来成交": 1},
    {"id": "D2", "姓名": "李师傅", "车队": "顺达", "车型": "9.6米厢式", "城市": "北京",
     "常跑线路": {"北京-天津"}, "历史成交": 15, "均价": 1300,
     "新司机": False, "浏览过本线路": False, "后来成交": 0},
    {"id": "D3", "姓名": "王师傅", "车队": "个体·王", "车型": "9.6米厢式", "城市": "北京",
     "常跑线路": {"北京-天津", "天津-济南"}, "历史成交": 9, "均价": 1220,
     "新司机": False, "浏览过本线路": True, "后来成交": 1},
    {"id": "D4", "姓名": "赵师傅", "车队": "个体", "车型": "13米高栏", "城市": "北京",
     "常跑线路": {"北京-天津"}, "历史成交": 30, "均价": 1500,
     "新司机": False, "浏览过本线路": True, "后来成交": 0},
    {"id": "D5", "姓名": "刘师傅", "车队": "个体·刘", "车型": "9.6米厢式", "城市": "北京",
     "常跑线路": set(), "历史成交": 0, "均价": 1250,
     "新司机": True, "浏览过本线路": True, "后来成交": 0},
    {"id": "D6", "姓名": "陈师傅", "车队": "个体", "车型": "9.6米厢式", "城市": "上海",
     "常跑线路": {"上海-南京"}, "历史成交": 18, "均价": 1300,
     "新司机": False, "浏览过本线路": False, "后来成交": 0},
    {"id": "D7", "姓名": "孙师傅", "车队": "个体", "车型": "9.6米厢式", "城市": "北京",
     "常跑线路": {"北京-石家庄"}, "历史成交": 5, "均价": 1200,
     "新司机": False, "浏览过本线路": False, "后来成交": 0},
]

# 每名司机到装货地的接单距离（公里），特征表里的一列。
DISTANCE = {"D1": 30, "D2": 25, "D3": 15, "D5": 20, "D7": 40}


def hard_filter(drivers, query):
    """硬过滤：车型、常驻城市不满足直接丢弃，不交给模型（第 2 课）。"""
    kept = []
    dropped = []
    for d in drivers:
        if d["车型"] != query["车型"]:          # 车型不一致 -> 物理上装不了
            dropped.append((d["id"], "车型不符"))
        elif d["城市"] != query["出发地"]:       # 人不在装货城市 -> 明早赶不到
            dropped.append((d["id"], "不在装货城市"))
        else:
            kept.append(d)
    return kept, dropped


def recall_two_channels(kept, query):
    """两路召回合并去重：路线一路、行为一路（第 2 课）。输入是硬过滤后的司机。"""
    lane = query["出发地"] + "-" + query["目的地"]
    # 路线一路：常跑线路包含这条线路的司机
    by_lane = {d["id"] for d in kept if lane in d["常跑线路"]}
    # 行为一路：最近浏览过本线路货源的司机
    by_behavior = {d["id"] for d in kept if d["浏览过本线路"]}
    merged = by_lane | by_behavior                      # 并集合并
    return sorted(merged), by_lane, by_behavior, lane


def build_features(candidates, query, distance):
    """特征表：只放打分前能查到的列（第 3 课）。价格偏离 = (报价 - 司机均价) / 司机均价。"""
    lane = query["出发地"] + "-" + query["目的地"]
    rows = []
    for d in candidates:
        lane_avg = LANE_AVG_PRICE.get(lane)             # 新线路查不到均价 -> None（第 5 课冷启动）
        if lane_avg is None or d["均价"] == 0:
            deviation = None                            # 缺失显式记 None，不填 0
        else:
            deviation = (query["报价"] - d["均价"]) / d["均价"]
        rows.append({
            "id": d["id"],
            "历史成交": d["历史成交"],
            "常跑命中": 1 if lane in d["常跑线路"] else 0,
            "接单距离": distance.get(d["id"], 50),
            "价格偏离": deviation,
            "新司机": d["新司机"],
        })
    return rows


def score(features):
    """可解释的固定权重打分（第 3 课的形状）：列乘系数再相加。"""
    scores = {}
    for f in features:
        s = 0.05 * f["历史成交"]                        # 历史成交越多越好
        s += 0.3 * f["常跑命中"]                        # 常跑这条线路加分
        s -= 0.01 * f["接单距离"]                       # 距离越远越差
        if f["价格偏离"] is not None and f["价格偏离"] > 0:
            s -= 3.0 * f["价格偏离"]                    # 报价高于线路均价要压分
        scores[f["id"]] = round(s, 2)
    return scores


def rerank(ranked_ids, scores, drivers):
    """重排：规则对分数的最后一道修改（第 5 课）。每条规则打印保护了谁、挤掉了谁。"""
    order = list(ranked_ids)
    # 规则一：同车队去重——一页名单不都给同一个车队。
    seen_fleets = set()
    deduped = []
    for did in order:
        d = next(x for x in drivers if x["id"] == did)
        if d["车队"] in seen_fleets:
            print(f"  [同车队去重] {did}（{d['车队']}）分数 {scores[did]} 被挤掉")
        else:
            seen_fleets.add(d["车队"])
            deduped.append(did)
    # 规则二：新司机保曝光——前 2 位至少一名新司机，用真实位置交换实现。
    top_n = deduped[:2]
    has_new = any(next(x for x in drivers if x["id"] == did)["新司机"] for did in top_n)
    if not has_new:
        for i, did in enumerate(deduped):
            d = next(x for x in drivers if x["id"] == did)
            if d["新司机"]:
                print(f"  [新司机保曝光] {did}（分数 {scores[did]}）与第 2 位交换")
                deduped[i], deduped[1] = deduped[1], deduped[i]
                break
    return deduped


def precision_at_k(ranked_ids, drivers, k):
    """precision@k：前 k 名里真实成交的比例（第 4 课）。标签是事后才有的。"""
    labels = {d["id"]: d["后来成交"] for d in drivers}
    top = ranked_ids[:k]
    hits = sum(labels[did] for did in top)
    return hits / k, [(did, labels[did]) for did in top]


def main():
    print("查询货：", QUERY)
    print()

    # 1. 硬过滤
    kept, dropped = hard_filter(DRIVERS, QUERY)
    print("【第 1 步 硬过滤】保留:", [d["id"] for d in kept])
    for did, reason in dropped:
        print(f"  丢弃 {did}: {reason}")
    print()

    # 2. 两路召回合并去重
    merged, by_lane, by_behavior, lane = recall_two_channels(kept, QUERY)
    print(f"【第 2 步 召回】线路倒排（{lane}）: {sorted(by_lane)}")
    print(f"              行为一路（浏览过）: {sorted(by_behavior)}")
    print("  合并去重后候选:", merged)
    print()

    # 3. 特征表
    features = build_features([d for d in kept if d["id"] in merged], QUERY, DISTANCE)
    print("【第 3 步 特征表】(打分前能查到的列)")
    for f in features:
        print("  ", f)
    print()

    # 4. 规则打分
    scores = score(features)
    ranked = sorted(scores, key=lambda did: scores[did], reverse=True)
    print("【第 4 步 打分】", scores)
    print("  纯分数排序:", ranked)
    print()

    # 5. 重排
    print("【第 5 步 重排】")
    final = rerank(ranked, scores, DRIVERS)
    print("  最终名单:", final)
    print()

    # 6. 精确率
    p, top_labels = precision_at_k(final, DRIVERS, 2)
    print(f"【第 6 步 精确率】precision@2 = {p}（前 2 名标签: {top_labels}）")
    miss = [did for did, hit in top_labels if not hit]
    print("  未成交却排进前 2 的:", miss, "——新司机保曝光的位置代价")


# ===== 课后作业 =====
# 完成后把 main() 末尾的注释去掉，单独运行 homework()。
# def homework():
#     """两道题，都用本文件已有的数据结构，不引入新依赖。
#
#     题 1（冷启动，第 5 课）：在 QUERY 里把目的地改成"石家庄"。
#     LANE_AVG_PRICE 里没有"北京-石家庄"这一条，观察 build_features 的价格偏离
#     变成 None、score 的惩罚项被跳过——这就是新线路"数据不足"的处理。
#     再想一步：如果给缺失的偏离填 0，谁会因此不公平地涨分？
#
#     题 2（召回率，第 4 课）：写一个 recall_at_k(ranked_ids, drivers, k)。
#     分母是整个司机池里"后来成交 = 1"的司机数，分子是前 k 名里的成交数。
#     用 k=3 跑一遍，回答：precision@2 = 0.5 时 recall@3 是多少？
#     被保曝光规则挤到第 3 位的那名司机，标签是什么？
#     """
#     print("作业未实现：请补全 homework() 后取消本行注释")


if __name__ == "__main__":
    main()
    # homework()   # 作业完成后取消注释单独运行
