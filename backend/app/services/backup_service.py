import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from sqlalchemy.orm import Session

from ..database import SQLALCHEMY_DATABASE_URL, engine
from ..migrations import run_migrations
from ..models import Setting

DEFAULT_RETENTION_DAYS = 7
RETENTION_KEY = "backup_retention_days"

BACKUP_NAME_RE = re.compile(r"^(?:manual-|pre-restore-)?dc_inventory_\d{8}_\d{6}\.db$")


def db_path() -> Path:
    assert SQLALCHEMY_DATABASE_URL.startswith("sqlite:///")
    return Path(SQLALCHEMY_DATABASE_URL[len("sqlite:///"):]).resolve()


def backup_dir() -> Path:
    d = db_path().parent / "backups"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _online_copy(src: Path, dst: Path):
    """sqlite 在线备份 API，源库使用中也能安全拷贝"""
    src_con = sqlite3.connect(str(src), timeout=30)
    dst_con = sqlite3.connect(str(dst), timeout=30)
    try:
        src_con.backup(dst_con)
    finally:
        src_con.close()
        dst_con.close()


def create_backup(prefix: str = "manual-") -> dict:
    name = f"{prefix}dc_inventory_{datetime.now():%Y%m%d_%H%M%S}.db"
    dst = backup_dir() / name
    _online_copy(db_path(), dst)
    return {"name": name, "size": dst.stat().st_size}


def list_backups() -> list[dict]:
    items = []
    for f in sorted(backup_dir().glob("*.db"), reverse=True):
        if not BACKUP_NAME_RE.match(f.name):
            continue
        stat = f.stat()
        if f.name.startswith("manual-"):
            kind = "手动"
        elif f.name.startswith("pre-restore-"):
            kind = "回退前自动"
        else:
            kind = "每日自动"
        items.append({
            "name": f.name,
            "size": stat.st_size,
            "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(sep=" ", timespec="seconds"),
            "kind": kind,
        })
    return items


def restore_backup(name: str):
    if not BACKUP_NAME_RE.match(name):
        raise ValueError("非法的备份文件名")
    src = backup_dir() / name
    if not src.exists():
        raise FileNotFoundError("备份文件不存在")
    # 回退前先对当前数据做一次安全快照
    create_backup(prefix="pre-restore-")
    _online_copy(src, db_path())
    # 旧备份可能是升级前的结构，恢复后立即补迁移，避免 ORM 引用缺列报错
    run_migrations(engine)


def delete_backup(name: str):
    if not BACKUP_NAME_RE.match(name):
        raise ValueError("非法的备份文件名")
    f = backup_dir() / name
    if f.exists():
        f.unlink()


def prune_old_backups(retention_days: int):
    cutoff = time.time() - retention_days * 86400
    for item in list_backups():
        f = backup_dir() / item["name"]
        if f.stat().st_mtime < cutoff:
            f.unlink()


def get_retention_days(db: Session) -> int:
    row = db.get(Setting, RETENTION_KEY)
    if row:
        try:
            return max(1, int(row.value))
        except ValueError:
            pass
    return DEFAULT_RETENTION_DAYS


def set_retention_days(db: Session, days: int):
    row = db.get(Setting, RETENTION_KEY)
    if row:
        row.value = str(days)
    else:
        db.add(Setting(key=RETENTION_KEY, value=str(days)))
    db.commit()


# ---------- 每日自动备份线程 ----------
_auto_thread_started = False


def _auto_backup_loop():
    from ..database import SessionLocal

    while True:
        try:
            today = datetime.now().strftime("%Y%m%d")
            has_today = any(
                b["name"].startswith(f"dc_inventory_{today}") for b in list_backups()
            )
            if not has_today:
                create_backup(prefix="")
                with SessionLocal() as session:
                    prune_old_backups(get_retention_days(session))
        except Exception:
            pass  # 自动备份失败不影响主服务，下个周期重试
        time.sleep(3600)


def start_auto_backup():
    global _auto_thread_started
    if not _auto_thread_started:
        _auto_thread_started = True
        t = threading.Thread(target=_auto_backup_loop, daemon=True)
        t.start()
