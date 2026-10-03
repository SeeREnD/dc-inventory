from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import hash_password
from .database import Base, SessionLocal, engine
from .migrations import run_migrations
from .models import User
from .routers import backup, changes, equipment, excel, rooms, stats, users
from .services.backup_service import start_auto_backup

Base.metadata.create_all(bind=engine)
run_migrations(engine)


def create_default_admin():
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role="admin",
                )
            )
            db.commit()
    finally:
        db.close()


create_default_admin()
start_auto_backup()

app = FastAPI(title="数据中心设备台账系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(users.users_router)
app.include_router(rooms.router)
app.include_router(equipment.router)
app.include_router(changes.router)
app.include_router(stats.router)
app.include_router(excel.router)
app.include_router(backup.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
