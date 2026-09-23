from pydantic import BaseModel

class EstimateRequest(BaseModel):
    room_id: int
    coats: int | None = None
    coverage: float | None = None
    persist: bool = True

class RoomEstimateParam(BaseModel):
    """分房覆盖参数；缺省字段回落到统一 coats/coverage 与全局设置。"""
    room_id: int
    coats: int | None = None
    coverage: float | None = None

class MultiEstimateRequest(BaseModel):
    room_ids: list[int]
    coats: int | None = None
    coverage: float | None = None
    room_params: list[RoomEstimateParam] | None = None
    persist: bool = True
