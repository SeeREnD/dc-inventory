from fastapi import Request
from sqlalchemy.orm import Session

from .models import AuditLog


def log_audit(
    db: Session, username: str, action: str, detail: dict | None = None, ip: str | None = None
):
    db.add(AuditLog(username=username, action=action, detail=detail, ip=ip))


def client_ip(request: Request) -> str | None:
    # 经过 nginx 反代时取 X-Forwarded-For
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None
