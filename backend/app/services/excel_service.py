import io
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from ..models import Cabinet, ChangeLog, Equipment, Room

HEADERS = [
    "资产编号", "设备名称", "类型", "品牌", "型号", "SN序列号",
    "机房", "机柜", "U位", "IP", "状态", "采购日期", "保修到期",
    "责任人", "备注",
]

VALID_STATUS = ("在用", "备用", "维修", "报废", "退役")
VALID_CATEGORY = ("服务器", "交换机", "存储", "防火墙", "其他")


def generate_template() -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "设备台账"
    ws.append(HEADERS)
    ws.append(
        ["DC-2026-0001", "示例服务器", "服务器", "Dell", "R740",
         "SN123456", "机房A", "A-01", "U10", "192.168.1.10", "在用",
         "2025-01-15", "2028-01-15", "张三", "示例数据，导入时会自动更新该行"]
    )
    for col, width in zip("ABCDEFGHIJKLMNO", [14, 16, 10, 10, 16, 16, 10, 10, 8, 14, 8, 12, 12, 10, 20]):
        ws.column_dimensions[col].width = width
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def export_equipment(rows: list[Equipment]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "设备台账"
    ws.append(HEADERS)
    for e in rows:
        ws.append(
            [
                e.asset_no, e.name, e.category, e.brand, e.model, e.sn,
                e.room.name if e.room else None,
                e.cabinet.name if e.cabinet else None,
                e.u_position, e.ip, e.status,
                e.purchase_date.isoformat() if e.purchase_date else None,
                e.warranty_end.isoformat() if e.warranty_end else None,
                e.owner, e.remark,
            ]
        )
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _parse_date(value) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value).strip())


def _get_or_create_room(db: Session, name: str | None) -> Room | None:
    if not name:
        return None
    name = str(name).strip()
    room = db.query(Room).filter(Room.name == name).first()
    if not room:
        room = Room(name=name)
        db.add(room)
        db.flush()
    return room


def _find_cabinet(db: Session, room: Room | None, name) -> Cabinet | None:
    if not room or name in (None, ""):
        return None
    return (
        db.query(Cabinet)
        .filter(Cabinet.room_id == room.id, Cabinet.name == str(name).strip())
        .first()
    )


def import_equipment(db: Session, content: bytes, operator_id: int | None) -> dict:
    wb = load_workbook(io.BytesIO(content), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(min_row=2, values_only=True))

    created = updated = failed = 0
    errors: list[str] = []

    for idx, row in enumerate(rows, start=2):
        if not row or not row[0]:
            continue  # 空行跳过
        try:
            (
                asset_no, name, category, brand, model, sn,
                room_name, cabinet_name, u_position, ip, status,
                purchase_date, warranty_end, owner, remark,
            ) = [str(v).strip() if v is not None else None for v in row[:15]]

            if not asset_no or not name or not category:
                raise ValueError("资产编号、设备名称、类型为必填项")
            if category not in VALID_CATEGORY:
                raise ValueError(f"类型必须是 {'/'.join(VALID_CATEGORY)}")
            if status is None:
                status = "在用"
            if status not in VALID_STATUS:
                raise ValueError(f"状态必须是 {'/'.join(VALID_STATUS)}")

            room = _get_or_create_room(db, room_name)
            cabinet = _find_cabinet(db, room, cabinet_name)

            data = dict(
                name=name, category=category, brand=brand, model=model, sn=sn,
                room_id=room.id if room else None,
                cabinet_id=cabinet.id if cabinet else None,
                u_position=u_position, ip=ip, status=status,
                purchase_date=_parse_date(purchase_date),
                warranty_end=_parse_date(warranty_end),
                owner=owner, remark=remark,
            )

            existing = (
                db.query(Equipment).filter(Equipment.asset_no == asset_no).first()
            )
            if existing:
                if data["sn"]:
                    sn_dup = (
                        db.query(Equipment)
                        .filter(Equipment.sn == data["sn"], Equipment.id != existing.id)
                        .first()
                    )
                    if sn_dup:
                        raise ValueError(f"SN 序列号 {data['sn']} 已被其他设备使用")
                for k, v in data.items():
                    setattr(existing, k, v)
                created_flag = False
            else:
                if data["sn"] and (
                    db.query(Equipment).filter(Equipment.sn == data["sn"]).first()
                ):
                    raise ValueError(f"SN 序列号 {data['sn']} 已被其他设备使用")
                existing = Equipment(asset_no=asset_no, **data)
                db.add(existing)
                created_flag = True

            db.flush()
            db.add(
                ChangeLog(
                    equipment_id=existing.id,
                    asset_no=asset_no,
                    action="导入",
                    detail={"created": created_flag},
                    operator_id=operator_id,
                )
            )
            if created_flag:
                created += 1
            else:
                updated += 1
        except Exception as exc:  # noqa: BLE001 - 逐行收集错误继续导入
            failed += 1
            errors.append(f"第 {idx} 行：{exc}")

    db.commit()
    return {"created": created, "updated": updated, "failed": failed, "errors": errors}
