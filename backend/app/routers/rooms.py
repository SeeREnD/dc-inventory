from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import require_role
from ..database import get_db
from ..models import Cabinet, Equipment, Room

router = APIRouter(prefix="/api", tags=["rooms"])

editor_required = Depends(require_role("admin", "editor"))


# ---------- 机房 ----------
@router.get("/rooms", response_model=list[schemas.RoomOut])
def list_rooms(db: Session = Depends(get_db)):
    return db.query(Room).order_by(Room.id).all()


@router.post("/rooms", response_model=schemas.RoomOut)
def create_room(
    body: schemas.RoomIn, db: Session = Depends(get_db), _: None = editor_required
):
    if db.query(Room).filter(Room.name == body.name).first():
        raise HTTPException(status_code=400, detail="机房名称已存在")
    room = Room(**body.model_dump())
    db.add(room)
    db.commit()
    db.refresh(room)
    return room


@router.put("/rooms/{room_id}", response_model=schemas.RoomOut)
def update_room(
    room_id: int,
    body: schemas.RoomIn,
    db: Session = Depends(get_db),
    _: None = editor_required,
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    dup = db.query(Room).filter(Room.name == body.name, Room.id != room_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="机房名称已存在")
    for k, v in body.model_dump().items():
        setattr(room, k, v)
    db.commit()
    db.refresh(room)
    return room


@router.delete("/rooms/{room_id}")
def delete_room(
    room_id: int, db: Session = Depends(get_db), _: None = editor_required
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="机房不存在")
    if db.query(Cabinet).filter(Cabinet.room_id == room_id).first():
        raise HTTPException(status_code=400, detail="该机房下还有机柜，无法删除")
    db.delete(room)
    db.commit()
    return {"msg": "删除成功"}


# ---------- 机柜 ----------
@router.get("/cabinets", response_model=list[schemas.CabinetOut])
def list_cabinets(room_id: int | None = None, db: Session = Depends(get_db)):
    q = db.query(Cabinet)
    if room_id is not None:
        q = q.filter(Cabinet.room_id == room_id)
    items = q.order_by(Cabinet.room_id, Cabinet.name).all()
    out = []
    for c in items:
        item = schemas.CabinetOut.model_validate(c)
        item.room_name = c.room.name if c.room else None
        out.append(item)
    return out


@router.post("/cabinets", response_model=schemas.CabinetOut)
def create_cabinet(
    body: schemas.CabinetIn, db: Session = Depends(get_db), _: None = editor_required
):
    if not db.query(Room).filter(Room.id == body.room_id).first():
        raise HTTPException(status_code=400, detail="机房不存在")
    dup = (
        db.query(Cabinet)
        .filter(Cabinet.room_id == body.room_id, Cabinet.name == body.name)
        .first()
    )
    if dup:
        raise HTTPException(status_code=400, detail="该机房下机柜名称已存在")
    cabinet = Cabinet(**body.model_dump())
    db.add(cabinet)
    db.commit()
    db.refresh(cabinet)
    return cabinet


@router.put("/cabinets/{cabinet_id}", response_model=schemas.CabinetOut)
def update_cabinet(
    cabinet_id: int,
    body: schemas.CabinetIn,
    db: Session = Depends(get_db),
    _: None = editor_required,
):
    cabinet = db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()
    if not cabinet:
        raise HTTPException(status_code=404, detail="机柜不存在")
    for k, v in body.model_dump().items():
        setattr(cabinet, k, v)
    db.commit()
    db.refresh(cabinet)
    return cabinet


@router.delete("/cabinets/{cabinet_id}")
def delete_cabinet(
    cabinet_id: int, db: Session = Depends(get_db), _: None = editor_required
):
    cabinet = db.query(Cabinet).filter(Cabinet.id == cabinet_id).first()
    if not cabinet:
        raise HTTPException(status_code=404, detail="机柜不存在")
    if db.query(Equipment).filter(Equipment.cabinet_id == cabinet_id).first():
        raise HTTPException(status_code=400, detail="该机柜下还有设备，无法删除")
    db.delete(cabinet)
    db.commit()
    return {"msg": "删除成功"}
