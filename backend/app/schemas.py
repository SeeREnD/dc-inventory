from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ---------- Auth / User ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    username: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str
    is_active: bool
    created_at: datetime


class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "viewer"


class UserUpdate(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


# ---------- Room / Cabinet ----------
class RoomIn(BaseModel):
    name: str
    location: Optional[str] = None
    remark: Optional[str] = None


class RoomOut(RoomIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CabinetIn(BaseModel):
    room_id: int
    name: str
    capacity_u: int = 42
    remark: Optional[str] = None


class CabinetOut(CabinetIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_name: Optional[str] = None


# ---------- Equipment ----------
class EquipmentIn(BaseModel):
    asset_no: str
    name: str
    category: str
    brand: Optional[str] = None
    model: Optional[str] = None
    sn: Optional[str] = None
    room_id: Optional[int] = None
    cabinet_id: Optional[int] = None
    u_position: Optional[str] = None
    ip: Optional[str] = None
    status: str = "在用"
    purchase_date: Optional[date] = None
    warranty_end: Optional[date] = None
    owner: Optional[str] = None
    remark: Optional[str] = None


class EquipmentOut(EquipmentIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_name: Optional[str] = None
    cabinet_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class EquipmentListOut(BaseModel):
    total: int
    items: list[EquipmentOut]


# ---------- ChangeLog ----------
class ChangeLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    equipment_id: int
    asset_no: str
    action: str
    detail: Optional[dict] = None
    operator: Optional[str] = None
    created_at: datetime


class ChangeLogListOut(BaseModel):
    total: int
    items: list[ChangeLogOut]


# ---------- Excel / Stats ----------
class ImportReport(BaseModel):
    created: int
    updated: int
    failed: int
    errors: list[str]


class StatsOut(BaseModel):
    total: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    by_room: dict[str, int]
    expiring_warranty: list[dict]


# ---------- Audit / Backup ----------
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    action: str
    detail: Optional[dict] = None
    ip: Optional[str] = None
    created_at: datetime


class AuditLogListOut(BaseModel):
    total: int
    items: list[AuditLogOut]


class BackupInfo(BaseModel):
    name: str
    size: int
    created_at: str
    kind: str


class BackupSettings(BaseModel):
    retention_days: int = 7
