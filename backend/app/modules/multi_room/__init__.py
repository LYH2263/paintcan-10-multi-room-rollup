"""多房间合并用量模块：校验一组房间编号并按各房当前洞口、统一或分房参数汇总升数。

只做纯计算/校验，不触碰数据库；输入的每个房间为
{"room_id","name","length","width","height","openings":[{"w","h"}]}。
coverage/coats 既可传统一标量，也可传 {room_id: 值} 分房映射（由 service 层
把缺省房间填好后传入）。
分房结果为快照（含房间名/尺寸/洞口/升数），由上层钉选进 calc_runs，
之后房间尺寸或洞口被修改不会影响历史记录。
"""

class MultiRoomError(ValueError):
    """房间编号列表非法（为空或含重复编号）。"""

class RoomNotFoundError(LookupError):
    """列表中存在不存在的房间编号。missing 为首个不存在的编号。"""
    def __init__(self, missing):
        self.missing = missing
        super().__init__(f"room_id 不存在: {missing}")

def validate_ids(room_ids):
    ids = [int(i) for i in (room_ids or [])]
    if not ids:
        raise MultiRoomError("room_ids 不能为空")
    if len(set(ids)) != len(ids):
        raise MultiRoomError("room_ids 含重复编号")
    return ids

def _value_for(spec, rid):
    """统一标量直接用；分房映射按编号取值（容忍字符串键）。"""
    if isinstance(spec, dict):
        return spec[rid] if rid in spec else spec[str(rid)]
    return spec

def build_breakdown(rooms, room_ids, coverage, coats, estimate_fn):
    """按编号顺序计算各房升数。rooms 必须已覆盖全部编号，否则 RoomNotFoundError。

    estimate_fn(length, width, height, openings, coverage, coats) -> dict，
    与单房 engines.estimate.estimate_room 相同，保证单房口径一致。
    """
    by_id = {int(r["room_id"]): r for r in rooms}
    for rid in room_ids:
        if rid not in by_id:
            raise RoomNotFoundError(rid)
    breakdown, total = [], 0.0
    for rid in room_ids:
        r = by_id[rid]
        cov = float(_value_for(coverage, rid))
        ct = int(_value_for(coats, rid))
        ops = [{"w": float(o["w"]), "h": float(o["h"])} for o in r.get("openings", [])]
        e = estimate_fn(r["length"], r["width"], r["height"], ops, cov, ct)
        total += float(e["liters"])
        breakdown.append({
            "room_id": rid, "name": r.get("name"),
            "length": r["length"], "width": r["width"], "height": r["height"],
            "gross_m2": e["gross_m2"], "openings_m2": e["openings_m2"], "net_m2": e["net_m2"],
            "coverage": cov, "coats": ct, "liters": e["liters"],
        })
    return {"rooms": breakdown, "total_liters": round(total, 2)}
