from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import ChangeLog, User

router = APIRouter(prefix="/api/changes", tags=["changes"])


@router.get("", response_model=schemas.ChangeLogListOut)
def list_changes(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    equipment_id: int | None = None,
    action: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from ..models import Equipment

    q = db.query(ChangeLog)
    if equipment_id is not None:
        q = q.filter(ChangeLog.equipment_id == equipment_id)
    if action:
        q = q.filter(ChangeLog.action == action)

    total = q.count()
    items = (
        q.order_by(ChangeLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    out = []
    for c in items:
        item = schemas.ChangeLogOut.model_validate(c)
        operator = db.query(User).filter(User.id == c.operator_id).first()
        item.operator = operator.username if operator else None
        out.append(item)
    return schemas.ChangeLogListOut(total=total, items=out)
