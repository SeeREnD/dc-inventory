import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./dc_inventory.db")

# SQLite 单文件 + 并发写入场景下，开启 WAL 并加大 busy 超时，避免 "database is locked"
_connect_args = {"check_same_thread": False}
if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
    _connect_args["timeout"] = 30

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)


def _enable_wal():
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            conn.exec_driver_sql("PRAGMA busy_timeout=30000")


_enable_wal()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
