"""Các mô hình dữ liệu (validate đầu vào cho API)."""
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class FloodPointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    lng: float = Field(ge=-180, le=180, description="Kinh độ")
    lat: float = Field(ge=-90, le=90, description="Vĩ độ")
    sensor_id: Optional[str] = Field(default=None, max_length=60)
    threshold_cm: int = Field(default=20, ge=1, le=200)


class FloodPointUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    lng: Optional[float] = Field(default=None, ge=-180, le=180)
    lat: Optional[float] = Field(default=None, ge=-90, le=90)
    sensor_id: Optional[str] = Field(default=None, max_length=60)
    threshold_cm: Optional[int] = Field(default=None, ge=1, le=200)

    @model_validator(mode="after")
    def lng_lat_together(self):
        if (self.lng is None) != (self.lat is None):
            raise ValueError("Phải gửi cả lng và lat cùng nhau (hoặc không gửi cả hai)")
        return self


class ReadingCreate(BaseModel):
    """Số đo mực nước. Gửi kèm point_id HOẶC sensor_id."""
    depth_cm: float = Field(ge=0, le=500)
    point_id: Optional[int] = None
    sensor_id: Optional[str] = None
    source: Literal["sensor", "crowd", "ai"] = "sensor"

    @model_validator(mode="after")
    def need_point_or_sensor(self):
        if self.point_id is None and not self.sensor_id:
            raise ValueError("Cần gửi point_id hoặc sensor_id")
        return self


class ReportCreate(BaseModel):
    lng: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)
    level: Literal["light", "medium", "heavy"]
    user_id: Optional[int] = None
    photo_url: Optional[str] = Field(default=None, max_length=500)


class ReportClear(BaseModel):
    """Người dùng báo 'đã hết ngập' tại vị trí của họ."""
    lng: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


class LngLat(BaseModel):
    lng: float = Field(ge=-180, le=180)
    lat: float = Field(ge=-90, le=90)


class RouteRequest(BaseModel):
    origin: LngLat
    destination: LngLat
    vehicle: Literal["motorbike", "car"] = "motorbike"
