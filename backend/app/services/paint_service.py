from app.db import connect
from app.engines.estimate import estimate_room
from app.modules import multi_room
from app.repositories import openings, rooms, runs, settings

class PaintService:
    def __init__(self): self._c = connect()
    def close(self): self._c.close()
    def __enter__(self): return self
    def __exit__(self, *a): self.close()
    def list_rooms(self): return rooms.list_all(self._c)
    def room_detail(self, rid):
        r = rooms.get(self._c, rid)
        if not r: return None
        return {"room": r, "openings": openings.for_room(self._c, rid)}
    def settings(self): return settings.get_map(self._c)
    def history(self, limit=50): return runs.list_recent(self._c, limit)
    def estimate(self, room_id, persist, coats=None, coverage=None):
        detail = self.room_detail(room_id)
        if not detail: return None
        r = detail["room"]
        cov, ct = settings.coverage_coats(self._c)
        cov = float(coverage or cov)
        ct = int(coats or ct)
        ops = [{"w": o["w"], "h": o["h"]} for o in detail["openings"]]
        result = estimate_room(r["length"], r["width"], r["height"], ops, cov, ct)
        rid = runs.insert(self._c, "estimate", {"room_id": room_id, "coats": ct, "coverage": cov}, result, room_id) if persist else None
        return {"run_id": rid, "room_id": room_id, **result}
    def estimate_multi(self, room_ids, persist, coats=None, coverage=None, room_params=None):
        """多房间合并用量。非法编号整单拒绝（不写 calc_runs）。

        room_params: [{"room_id","coats","coverage"}]，仅覆盖指定房间，
        其余房间与未填字段回落到统一 coats/coverage 与全局设置。
        """
        ids = multi_room.validate_ids(room_ids)
        base_cov, base_ct = settings.coverage_coats(self._c)
        unified_cov = float(coverage) if coverage is not None else base_cov
        unified_ct = int(coats) if coats is not None else base_ct
        per = {}
        for p in room_params or []:
            pd = {"room_id": p.room_id, "coats": p.coats, "coverage": p.coverage}
            if pd["room_id"] in per:
                raise multi_room.MultiRoomError(f"room_params 含重复编号 {pd['room_id']}")
            per[pd["room_id"]] = pd
        loaded = []
        for rid in ids:
            detail = self.room_detail(rid)
            if not detail:
                raise multi_room.RoomNotFoundError(rid)
            r = detail["room"]
            loaded.append({
                "room_id": rid, "name": r["name"],
                "length": r["length"], "width": r["width"], "height": r["height"],
                "openings": [{"w": o["w"], "h": o["h"]} for o in detail["openings"]],
            })
        cov_map, ct_map = {}, {}
        for rid in ids:
            p = per.get(rid)
            cov_map[rid] = float(p["coverage"]) if p and p.get("coverage") is not None else unified_cov
            ct_map[rid] = int(p["coats"]) if p and p.get("coats") is not None else unified_ct
        result = multi_room.build_breakdown(loaded, ids, cov_map, ct_map, estimate_room)
        payload = {
            "room_ids": ids,
            "coats": coats, "coverage": coverage,
            "room_params": [{"room_id": per[rid]["room_id"], "coats": per[rid]["coats"],
                             "coverage": per[rid]["coverage"]} for rid in ids if rid in per],
        }
        run_id = runs.insert(self._c, "multi_estimate", payload, result, None) if persist else None
        return {"run_id": run_id, "room_ids": ids, **result}
    def dashboard(self):
        rs = rooms.list_all(self._c)
        return {"room_count": len(rs), "clean": len([x for x in rs if "种子" not in x["name"] and "多种" not in x["name"]]), "dirty": len([x for x in rs if "多种" in x["name"]])}
