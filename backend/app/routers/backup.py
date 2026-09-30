from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .. import schemas
from ..audit import client_ip, log_audit
from ..auth import require_role
from ..database import get_db
from ..models import AuditLog, User
from ..services import backup_service

router = APIRouter(
    prefix="/api",
    tags=["audit-backup"],
    dependencies=[Depends(require_role("admin"))],
)


# ---------- 审计日志 ----------
@router.get("/audit-logs", response_model=schemas.AuditLogListOut)
def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    action: str | None = None,
    username: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(AuditLog)
    if action:
        q = q.filter(AuditLog.action == action)
    if username:
        q = q.filter(AuditLog.username.like(f"%{username}%"))
    total = q.count()
    items = (
        q.order_by(AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return schemas.AuditLogListOut(total=total, items=items)


# ---------- 备份管理 ----------
@router.get("/backups", response_model=list[schemas.BackupInfo])
def list_backups():
    return backup_service.list_backups()


@router.post("/backups", response_model=schemas.BackupInfo)
def create_backup(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    info = backup_service.create_backup(prefix="manual-")
    log_audit(db, user.username, "创建备份", {"name": info["name"]}, client_ip(request))
    db.commit()
    return {**info, "created_at": "", "kind": "手动"}


@router.get("/backups/{name}/download")
def download_backup(name: str):
    path = backup_service.backup_dir() / name
    if not backup_service.BACKUP_NAME_RE.match(name) or not path.exists():
        raise HTTPException(status_code=404, detail="备份文件不存在")
    return FileResponse(path, filename=name, media_type="application/octet-stream")


@router.post("/backups/{name}/restore")
def restore_backup(
    name: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    try:
        backup_service.restore_backup(name)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="备份文件不存在")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_audit(db, user.username, "回退数据", {"from_backup": name}, client_ip(request))
    db.commit()
    return {"msg": "已回退到所选备份，当前数据已自动另存为安全快照"}


@router.delete("/backups/{name}")
def delete_backup(
    name: str,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    try:
        backup_service.delete_backup(name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    log_audit(db, user.username, "删除备份", {"name": name}, client_ip(request))
    db.commit()
    return {"msg": "已删除"}


@router.get("/backups/settings/retention", response_model=schemas.BackupSettings)
def get_retention(db: Session = Depends(get_db)):
    return schemas.BackupSettings(retention_days=backup_service.get_retention_days(db))


@router.put("/backups/settings/retention", response_model=schemas.BackupSettings)
def set_retention(
    body: schemas.BackupSettings,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(require_role("admin")),
):
    days = max(1, min(body.retention_days, 365))
    backup_service.set_retention_days(db, days)
    backup_service.prune_old_backups(days)
    log_audit(db, user.username, "修改备份保留时长", {"retention_days": days}, client_ip(request))
    db.commit()
    return schemas.BackupSettings(retention_days=days)
