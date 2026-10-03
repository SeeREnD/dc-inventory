from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, field_validator


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
class CpuSpec(BaseModel):
    model: Optional[str] = None
    sockets: Optional[int] = None          # 物理 CPU 颗数
    cores_per_cpu: Optional[int] = None    # 每颗核心数
    freq_ghz: Optional[float] = None       # 主频 GHz


class GpuSpec(BaseModel):
    model: Optional[str] = None
    count: Optional[int] = None            # 张数
    memory_gb: Optional[int] = None        # 单卡显存 GB
    purpose: Optional[str] = None          # 计算/推理/渲染/其他


class DiskSpec(BaseModel):
    type: Optional[str] = None             # SSD/SATA-SSD/NVMe/HDD
    capacity_gb: Optional[int] = None      # 单块容量 GB
    count: Optional[int] = None            # 块数
    raid_level: Optional[str] = None       # RAID0/1/5/6/10/直通
    role: Optional[str] = None             # 系统/数据/缓存


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
    # 网络地址：带内(业务网) / 带外(管理网,BMC) × IPv4 / IPv6
    ip_inband_v4: Optional[str] = None
    ip_inband_v6: Optional[str] = None
    ip_outband_v4: Optional[str] = None
    ip_outband_v6: Optional[str] = None
    # 硬件规格（数量不定，JSON 数组）
    cpus: Optional[list[CpuSpec]] = None
    gpus: Optional[list[GpuSpec]] = None
    disks: Optional[list[DiskSpec]] = None
    status: str = "在用"
    purchase_date: Optional[date] = None
    warranty_end: Optional[date] = None
    owner: Optional[str] = None
    remark: Optional[str] = None

    @field_validator("cpus", "gpus", "disks", mode="before")
    @classmethod
    def _ensure_list(cls, v):
        # 容错：脏数据/手工改库可能塞入非数组，统一降级为 None，避免整表接口 500
        if v is None or isinstance(v, list):
            return v
        return None


class EquipmentOut(EquipmentIn):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_name: Optional[str] = None
    cabinet_name: Optional[str] = None
    spec_summary: Optional[str] = None
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
    warnings: list[str] = []


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
