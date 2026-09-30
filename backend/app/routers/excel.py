from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..auth import get_current_user, require_role
from ..database import get_db
from ..models import Equipment, User
from ..services import excel_service

router = APIRouter(prefix="/api/excel", tags=["excel"])


@router.get("/template")
def download_template(_: User = Depends(get_current_user)):
    content = excel_service.generate_template()
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=template.xlsx"},
    )


@router.get("/export")
def export(
    keyword: str | None = None,
    status: str | None = None,
    category: str | None = None,
    room_id: int | None = None,
    cabinet_id: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    from .equipment import build_filtered_query

    # 与设备列表一致的筛选条件，导出当前筛选结果（上限 10000 行）
    q = build_filtered_query(db, keyword, status, category, room_id, cabinet_id)
    rows = q.order_by(Equipment.id).limit(10000).all()
    content = excel_service.export_equipment(rows)
    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=equipment.xlsx"},
    )


@router.post("/import", response_model=schemas.ImportReport)
def import_excel(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin", "editor")),
):
    content = file.file.read()
    report = excel_service.import_equipment(db, content, user.id)
    return schemas.ImportReport(**report)
