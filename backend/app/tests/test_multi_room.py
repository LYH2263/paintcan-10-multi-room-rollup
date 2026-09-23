import json
import os
import pytest

from app.schemas.estimate import RoomEstimateParam

@pytest.fixture()
def svc(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    import sys
    for m in [m for m in sys.modules if m == "app" or m.startswith("app.")]:
        del sys.modules[m]
    from app import seed
    from app.services.paint_service import PaintService
    seed.init_db()
    with PaintService() as s:
        yield s

def _single(s, rid, coats=None, coverage=None):
    return s.estimate(rid, False, coats, coverage)

from app.schemas.estimate import RoomEstimateParam

def test_single_room_matches_single_endpoint(svc):
    single = _single(svc, 1, coats=2, coverage=8)
    multi = svc.estimate_multi([1], False, coats=2, coverage=8)
    assert multi["total_liters"] == single["liters"]
    assert multi["rooms"][0]["liters"] == single["liters"]
    assert multi["run_id"] is None

def test_single_room_default_params_match(svc):
    single = _single(svc, 1)
    multi = svc.estimate_multi([1], False)
    assert multi["total_liters"] == single["liters"]

def test_multi_total_is_sum(svc):
    r = svc.estimate_multi([1, 2], False)
    assert r["total_liters"] == round(sum(x["liters"] for x in r["rooms"]), 2)
    assert [x["room_id"] for x in r["rooms"]] == [1, 2]

def test_per_room_params(svc):
    r = svc.estimate_multi([1, 2], False, coats=2, coverage=8,
                           room_params=[RoomEstimateParam(room_id=2, coats=1)])
    assert r["rooms"][0]["coats"] == 2
    assert r["rooms"][1]["coats"] == 1
    room2 = _single(svc, 2, coats=1, coverage=8)
    assert r["rooms"][1]["liters"] == room2["liters"]

def test_empty_rejected(svc):
    from app.modules.multi_room import MultiRoomError
    with pytest.raises(MultiRoomError):
        svc.estimate_multi([], True)
    assert svc.history() == [r for r in svc.history()]  # no exception; below asserts no write
    assert all(r["kind"] != "multi_estimate" for r in svc.history())

def test_duplicate_rejected_and_no_write(svc):
    from app.modules.multi_room import MultiRoomError
    before = len(svc.history())
    with pytest.raises(MultiRoomError):
        svc.estimate_multi([1, 1], True)
    assert len(svc.history()) == before

def test_nonexistent_rejected_and_no_write(svc):
    from app.modules.multi_room import RoomNotFoundError
    before = len(svc.history())
    with pytest.raises(RoomNotFoundError):
        svc.estimate_multi([1, 999], True)
    assert len(svc.history()) == before

def test_persist_writes_one_pinned_run(svc):
    r = svc.estimate_multi([1, 2], True)
    assert r["run_id"] is not None
    rows = [x for x in svc.history() if x["id"] == r["run_id"]]
    assert len(rows) == 1
    row = rows[0]
    assert row["kind"] == "multi_estimate"
    pinned = json.loads(row["result_json"])
    assert pinned["total_liters"] == r["total_liters"]
    assert [x["liters"] for x in pinned["rooms"]] == [x["liters"] for x in r["rooms"]]
    # 钉选：改其中一房层高后，旧合并记录分房升数不得跟着变
    old = [dict(x) for x in pinned["rooms"]]
    svc._c.execute("UPDATE rooms SET height=3.5 WHERE id=2")
    svc._c.commit()
    again = json.loads([x for x in svc.history() if x["id"] == r["run_id"]][0]["result_json"])
    assert [x["liters"] for x in again["rooms"]] == [x["liters"] for x in old]
    assert [x["height"] for x in again["rooms"]] == [2.8, 2.8]

def test_no_persist_writes_nothing(svc):
    before = len(svc.history())
    r = svc.estimate_multi([1, 2], False)
    assert r["run_id"] is None
    assert len(svc.history()) == before
