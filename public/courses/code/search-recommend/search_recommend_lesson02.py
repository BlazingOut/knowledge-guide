"""第 2 课：用倒排和多路合并完成一次召回。

默认入口只跑课程示例。课后作业的 homework() 不会被 main() 调用。
"""

from __future__ import annotations


# 8 票货。字段只用本课要演示的键：装货地、卸货地、车型、是否来得及。
CARGOS: dict[str, dict] = {
    "H1": {"origin": "北京", "dest": "天津", "vehicle": "9.6米", "ready": True},
    "H2": {"origin": "北京", "dest": "广州", "vehicle": "13米", "ready": True},
    "H3": {"origin": "北京", "dest": "天津", "vehicle": "9.6米", "ready": True},
    "H4": {"origin": "上海", "dest": "天津", "vehicle": "9.6米", "ready": True},
    "H5": {"origin": "北京", "dest": "天津", "vehicle": "4.2米", "ready": True},
    "H6": {"origin": "北京", "dest": "廊坊", "vehicle": "9.6米", "ready": True},
    "H7": {"origin": "北京", "dest": "武清", "vehicle": "9.6米", "ready": True},
    "H8": {"origin": "北京", "dest": "天津", "vehicle": "9.6米", "ready": True},
}

# 行为路的原始名单来自历史，不是货单字段。H2 用来演示硬过滤仍要把它丢掉。
BEHAVIOR_RAW = ["H3", "H7", "H2"]
# 地理路：卸货地在天津附近。H7 终点不是“天津”这两个字，精确倒排会漏。
GEO_NEAR_TIANJIN = ["H1", "H6", "H7"]

# 倒排路用这三个字段：装货地、车型、卸货地。三个都要和查询相同。
QUERY = {"origin": "北京", "vehicle": "9.6米", "dest": "天津"}


def passes_hard_filter(cargo: dict, query: dict) -> bool:
    """车型和装货地必须相同，而且司机来得及。卸货地不在这里判断。"""
    if cargo["vehicle"] != query["vehicle"]:
        return False
    if cargo["origin"] != query["origin"]:
        return False
    if not cargo["ready"]:
        return False
    return True


def hard_filter(cargos: dict[str, dict], query: dict) -> dict[str, dict]:
    """先留下能接的货。后面的倒排只建在这份小库上。"""
    return {
        cargo_id: cargo
        for cargo_id, cargo in cargos.items()
        if passes_hard_filter(cargo, query)
    }


def build_inverted_index(cargos: dict[str, dict], field: str) -> dict[str, list[str]]:
    """从“货单号 -> 属性”翻成“属性 -> 货单号”。同一个键按出现顺序追加。"""
    index: dict[str, list[str]] = {}
    for cargo_id, cargo in cargos.items():
        key = cargo[field]
        index.setdefault(key, []).append(cargo_id)
    return index


def intersect(left: list[str], right: list[str]) -> list[str]:
    """两路条件都要满足。保留 left 的顺序，避免同一查询多次运行结果抖动。"""
    seen = set(right)
    return [cargo_id for cargo_id in left if cargo_id in seen]


def drop_failed(cargo_ids: list[str], allowed: dict[str, dict]) -> tuple[list[str], list[str]]:
    """行为路、地理路可能带进硬过滤没通过的货。返回留下的和丢掉的。"""
    kept = [cargo_id for cargo_id in cargo_ids if cargo_id in allowed]
    dropped = [cargo_id for cargo_id in cargo_ids if cargo_id not in allowed]
    return kept, dropped


def merge_paths(paths: dict[str, list[str]]) -> list[dict]:
    """按货单号去重。先出现的路决定顺序，后出现的路只补充来源，不另开一条。"""
    order: list[str] = []
    sources: dict[str, list[str]] = {}
    for path_name, cargo_ids in paths.items():
        for cargo_id in cargo_ids:
            if cargo_id not in sources:
                sources[cargo_id] = []
                order.append(cargo_id)
            if path_name not in sources[cargo_id]:
                sources[cargo_id].append(path_name)
    return [{"id": cargo_id, "sources": sources[cargo_id]} for cargo_id in order]


def main() -> None:
    allowed = hard_filter(CARGOS, QUERY)
    dropped_by_hard = [cargo_id for cargo_id in CARGOS if cargo_id not in allowed]
    print("硬过滤丢掉:", dropped_by_hard)
    print("硬过滤留下:", list(allowed))

    origin_index = build_inverted_index(allowed, "origin")
    vehicle_index = build_inverted_index(allowed, "vehicle")
    dest_index = build_inverted_index(allowed, "dest")
    print("装货地倒排:", origin_index)
    print("车型倒排:", vehicle_index)
    print("卸货地倒排:", dest_index)

    by_origin_and_vehicle = intersect(
        origin_index[QUERY["origin"]],
        vehicle_index[QUERY["vehicle"]],
    )
    inverted_path = intersect(by_origin_and_vehicle, dest_index[QUERY["dest"]])
    behavior_path, behavior_dropped = drop_failed(BEHAVIOR_RAW, allowed)
    geo_path, geo_dropped = drop_failed(GEO_NEAR_TIANJIN, allowed)
    print("倒排路:", inverted_path)
    print("行为路:", behavior_path, "丢掉:", behavior_dropped)
    print("地理路:", geo_path, "丢掉:", geo_dropped)

    merged = merge_paths({
        "倒排": inverted_path,
        "行为": behavior_path,
        "地理": geo_path,
    })
    print("合并后（还没有名次）:")
    for item in merged:
        print(f"  {item['id']} 来源={item['sources']}")


# ===== 课后作业 =====
# 正文的倒排路已经同时比较装货地、车型和卸货地。
# 作业把卸货地单独做成一张表，再和只按装货地、车型取出的名单比较。
# 合并时每一路最多取 2 票。不要改上面的 main()。完成后单独调用 homework()。

def recall_exact_destination(cargos: dict[str, dict], destination: str) -> list[str]:
    """只按卸货地做倒排，返回卸货地正好等于 destination 的货单号。

    cargos 应是已经通过硬过滤的货。返回顺序与这些货在 cargos 中的顺序一致。
    """
    raise NotImplementedError


def merge_with_quota(paths: dict[str, list[str]], quota: int) -> list[dict]:
    """每一路最多放入 quota 票，再按货单号去重，并保留来源。

    某一路不足 quota 时，有几票算几票。
    同一货单号被多路找到时仍然只有一行，每一路都要记下来源。
    超过配额时，按该路原来的顺序保留前面的货。
    """
    raise NotImplementedError


def homework() -> None:
    """打印卸货地名单、只含装货地和车型的倒排名单，以及配额为 2 的合并结果。"""
    allowed = hard_filter(CARGOS, QUERY)
    origin_index = build_inverted_index(allowed, "origin")
    vehicle_index = build_inverted_index(allowed, "vehicle")
    origin_and_vehicle = intersect(
        origin_index[QUERY["origin"]],
        vehicle_index[QUERY["vehicle"]],
    )
    exact_dest = recall_exact_destination(allowed, "天津")
    checked = intersect(origin_and_vehicle, exact_dest)
    behavior_path, _ = drop_failed(BEHAVIOR_RAW, allowed)
    geo_path, _ = drop_failed(GEO_NEAR_TIANJIN, allowed)

    print("卸货地正好是天津:", exact_dest)
    print("装货地、车型再与卸货地比较:", checked)
    merged = merge_with_quota({
        "倒排": origin_and_vehicle,
        "行为": behavior_path,
        "地理": geo_path,
    }, quota=2)
    print("每一路最多 2 票:", merged)


if __name__ == "__main__":
    main()
    # homework()
