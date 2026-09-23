from fastapi import APIRouter, HTTPException
from app.modules import multi_room
from app.schemas.estimate import EstimateRequest, MultiEstimateRequest
from app.services.paint_service import PaintService
router = APIRouter()
@router.post("/estimate")
def post_estimate(body: EstimateRequest):
    with PaintService() as s:
        r = s.estimate(body.room_id, body.persist, body.coats, body.coverage)
        if not r: raise HTTPException(404)
        return r
@router.post("/estimate/multi")
def post_estimate_multi(body: MultiEstimateRequest):
    with PaintService() as s:
        try:
            return s.estimate_multi(body.room_ids, body.persist, body.coats, body.coverage,
                                    body.room_params)
        except multi_room.RoomNotFoundError as e:
            raise HTTPException(404, f"房间不存在: {e.missing}")
        except (multi_room.MultiRoomError, ValueError) as e:
            raise HTTPException(400, str(e))
