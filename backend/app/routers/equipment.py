from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user, require_role
from ..database import get_db
from ..models import Cabinet, ChangeLog, Equipment, Room, User

router = APIRouter(prefix="/api/equipment", tags=["equipment"])

VALID_STATUS = ("在用", "备用", "维修", "报废", "退役")
VALID_CATEGORY = ("服务器", "交换机", "存储", "防火墙", "其他")


def log_change(
    db: Session,
    equipment: Equipment,
    action: str,
    detail: dict | None,
    operator_id: int | None,
):
    db.add(
        ChangeLog(
            equipment_id=equipment.id,
            asset_no=equipment.asset_no,
            action=action,
            detail=detail,
            operator_id=operator_id,
        )
    )


def _json_safe(v):
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    return v


def to_out(e: Equipment) -> schemas.EquipmentOut:
    out = schemas.EquipmentOut.model_validate(e)
    out.room_name = e.room.name if e.room else None
    out.cabinet_name = e.cabinet.name if e.cabinet else None
    return out


# 允许排序的字段白名单，防注入
SORTABLE = {
    "asset_no": Equipment.asset_no,
    "name": Equipment.name,
    "warranty_end": Equipment.warranty_end,
    "purchase_date": Equipment.purchase_date,
    "created_at": Equipment.created_at,
    "id": Equipment.id,
}


def build_filtered_query(
    db: Session,
    keyword: str | None = None,
    status: str | None = None,
    category: str | None = None,
    room_id: int | None = None,
    cabinet_id: int | None = None,
):
    """设备列表与 Excel 导出共用的筛选条件"""
    q = db.query(Equipment)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(
            or_(
                Equipment.asset_no.like(kw),
                Equipment.name.like(kw),
                Equipment.sn.like(kw),
                Equipment.model.like(kw),
                Equipment.ip.like(kw),
                Equipment.owner.like(kw),
            )
        )
    if status:
        q = q.filter(Equipment.status == status)
    if category:
        q = q.filter(Equipment.category == category)
    if room_id is not None:
        q = q.filter(Equipment.room_id == room_id)
    if cabinet_id is not None:
        q = q.filter(Equipment.cabinet_id == cabinet_id)
    return q


@router.get("", response_model=schemas.EquipmentListOut)
def list_equipment(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: str | None = None,
    status: str | None = None,
    category: str | None = None,
    room_id: int | None = None,
    cabinet_id: int | None = None,
    sort_by: str | None = None,
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = build_filtered_query(db, keyword, status, category, room_id, cabinet_id)

    total = q.count()

    if sort_by and sort_by in SORTABLE:
        col = SORTABLE[sort_by]
        q = q.order_by(col.asc() if order == "asc" else col.desc())
    else:
        q = q.order_by(Equipment.id.desc())

    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return schemas.EquipmentListOut(
        total=total, items=[to_out(e) for e in items]
    )


@router.get("/{equipment_id}", response_model=schemas.EquipmentOut)
def get_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    e = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="设备不存在")
    return to_out(e)


@router.post("", response_model=schemas.EquipmentOut)
def create_equipment(
    body: schemas.EquipmentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "editor")),
):
    if db.query(Equipment).filter(Equipment.asset_no == body.asset_no).first():
        raise HTTPException(status_code=400, detail="资产编号已存在")
    if body.sn and db.query(Equipment).filter(Equipment.sn == body.sn).first():
        raise HTTPException(status_code=400, detail="SN 序列号已存在")
    if body.status not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="无效的设备状态")
    _validate_location(db, body.room_id, body.cabinet_id)

    e = Equipment(**body.model_dump())
    db.add(e)
    db.flush()
    log_change(db, e, "新增", body.model_dump(mode="json"), user.id)
    db.commit()
    db.refresh(e)
    return to_out(e)


@router.put("/{equipment_id}", response_model=schemas.EquipmentOut)
def update_equipment(
    equipment_id: int,
    body: schemas.EquipmentIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "editor")),
):
    e = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="设备不存在")
    dup_no = (
        db.query(Equipment)
        .filter(Equipment.asset_no == body.asset_no, Equipment.id != equipment_id)
        .first()
    )
    if dup_no:
        raise HTTPException(status_code=400, detail="资产编号已存在")
    if body.sn:
        dup_sn = (
            db.query(Equipment)
            .filter(Equipment.sn == body.sn, Equipment.id != equipment_id)
            .first()
        )
        if dup_sn:
            raise HTTPException(status_code=400, detail="SN 序列号已存在")
    if body.status not in VALID_STATUS:
        raise HTTPException(status_code=400, detail="无效的设备状态")
    _validate_location(db, body.room_id, body.cabinet_id)

    old = body.model_dump()
    changes = {
        k: {"old": _json_safe(getattr(e, k)), "new": _json_safe(v)}
        for k, v in old.items()
        if getattr(e, k) != v
    }
    for k, v in old.items():
        setattr(e, k, v)
    log_change(db, e, "编辑", changes, user.id)
    db.commit()
    db.refresh(e)
    return to_out(e)


@router.delete("/{equipment_id}")
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "editor")),
):
    e = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not e:
        raise HTTPException(status_code=404, detail="设备不存在")
    log_change(
        db, e, "删除", schemas.EquipmentOut.model_validate(e).model_dump(mode="json"), user.id
    )
    db.delete(e)
    db.commit()
    return {"msg": "删除成功"}


class BatchDeleteIn(schemas.BaseModel):
    ids: list[int]


@router.post("/batch-delete")
def batch_delete_equipment(
    body: BatchDeleteIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "editor")),
):
    if not body.ids:
        raise HTTPException(status_code=400, detail="未选择任何设备")
    items = db.query(Equipment).filter(Equipment.id.in_(body.ids)).all()
    for e in items:
        log_change(
            db, e, "删除",
            schemas.EquipmentOut.model_validate(e).model_dump(mode="json"), user.id,
        )
        db.delete(e)
    db.commit()
    return {"deleted": len(items)}


def _validate_location(db: Session, room_id: int | None, cabinet_id: int | None):
    if cabinet_id is not None:
        cabinet = db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()
        if not cabinet:
            raise HTTPException(status_code=400, detail="机柜不存在")
        if room_id is not None and cabinet.room_id != room_id:
            raise HTTPException(status_code=400, detail="机柜不属于所选机房")
    if room_id is not None:
        if not db.query(Room).filter(Room.id == room_id).first():
            raise HTTPException(status_code=400, detail="机房不存在")
