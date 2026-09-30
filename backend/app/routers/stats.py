from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user
from ..database import get_db
from ..models import Equipment, Room, User

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("", response_model=schemas.StatsOut)
def get_stats(
    db: Session = Depends(get_db), _: User = Depends(get_current_user)
):
    total = db.query(Equipment).count()

    by_status: dict[str, int] = {}
    by_category: dict[str, int] = {}
    by_room: dict[str, int] = {}
    expiring: list[dict] = []

    deadline = date.today() + timedelta(days=30)
    for e in db.query(Equipment).all():
        by_status[e.status] = by_status.get(e.status, 0) + 1
        by_category[e.category] = by_category.get(e.category, 0) + 1
        room_name = e.room.name if e.room else "未分配"
        by_room[room_name] = by_room.get(room_name, 0) + 1
        if e.warranty_end and date.today() <= e.warranty_end <= deadline:
            expiring.append(
                {
                    "id": e.id,
                    "asset_no": e.asset_no,
                    "name": e.name,
                    "warranty_end": e.warranty_end.isoformat(),
                    "room_name": room_name,
                }
            )
    expiring.sort(key=lambda x: x["warranty_end"])

    return schemas.StatsOut(
        total=total,
        by_status=by_status,
        by_category=by_category,
        by_room=by_room,
        expiring_warranty=expiring,
    )
