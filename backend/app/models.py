from datetime import datetime

from sqlalchemy import String, ForeignKey, Date, DateTime, Boolean, Integer, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(20), default="viewer")  # admin/editor/viewer
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Room(Base):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    location: Mapped[str | None] = mapped_column(String(200))
    remark: Mapped[str | None] = mapped_column(String(500))

    cabinets: Mapped[list["Cabinet"]] = relationship(back_populates="room")


class Cabinet(Base):
    __tablename__ = "cabinets"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    name: Mapped[str] = mapped_column(String(100))
    capacity_u: Mapped[int] = mapped_column(Integer, default=42)
    remark: Mapped[str | None] = mapped_column(String(500))

    room: Mapped["Room"] = relationship(back_populates="cabinets")


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(primary_key=True)
    asset_no: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(50))  # 服务器/交换机/存储/防火墙/其他
    brand: Mapped[str | None] = mapped_column(String(50))
    model: Mapped[str | None] = mapped_column(String(100))
    sn: Mapped[str | None] = mapped_column(String(100), unique=True)
    room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id"))
    cabinet_id: Mapped[int | None] = mapped_column(ForeignKey("cabinets.id"))
    u_position: Mapped[str | None] = mapped_column(String(20))
    # 网络地址：带内(业务网) / 带外(管理网,BMC/iDRAC) × IPv4 / IPv6
    ip_inband_v4: Mapped[str | None] = mapped_column(String(50))
    ip_inband_v6: Mapped[str | None] = mapped_column(String(50))
    ip_outband_v4: Mapped[str | None] = mapped_column(String(50))
    ip_outband_v6: Mapped[str | None] = mapped_column(String(50))
    # 硬件规格（数量不定，以 JSON 数组存储；仅作展示，不进筛选）
    cpus: Mapped[list | None] = mapped_column(JSON)
    gpus: Mapped[list | None] = mapped_column(JSON)
    disks: Mapped[list | None] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="在用")  # 在用/备用/维修/报废/退役
    purchase_date: Mapped[datetime | None] = mapped_column(Date)
    warranty_end: Mapped[datetime | None] = mapped_column(Date)
    owner: Mapped[str | None] = mapped_column(String(50))
    remark: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    room: Mapped["Room | None"] = relationship()
    cabinet: Mapped["Cabinet | None"] = relationship()


class ChangeLog(Base):
    __tablename__ = "change_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    equipment_id: Mapped[int] = mapped_column(ForeignKey("equipment.id"), index=True)
    asset_no: Mapped[str] = mapped_column(String(50))
    action: Mapped[str] = mapped_column(String(20))  # 新增/编辑/删除/导入
    detail: Mapped[dict | None] = mapped_column(JSON)
    operator_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditLog(Base):
    """系统审计日志：登录、退出、改密、用户管理、备份恢复等"""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), index=True)
    action: Mapped[str] = mapped_column(String(30), index=True)  # 登录成功/登录失败/退出/修改密码/创建用户...
    detail: Mapped[dict | None] = mapped_column(JSON)
    ip: Mapped[str | None] = mapped_column(String(50))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Setting(Base):
    """键值配置：备份保留天数等"""

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(50), primary_key=True)
    value: Mapped[str] = mapped_column(String(200))
