from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from .. import schemas
from ..audit import client_ip, log_audit
from ..auth import (
    create_access_token,
    get_current_user,
    hash_password,
    require_role,
    verify_password,
)
from ..database import get_db
from ..models import User

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=schemas.TokenResponse)
def login(body: schemas.LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = client_ip(request)
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not verify_password(body.password, user.password_hash):
        log_audit(db, body.username, "登录失败", ip=ip)
        db.commit()
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    if not user.is_active:
        log_audit(db, body.username, "登录失败", {"reason": "账号已禁用"}, ip)
        db.commit()
        raise HTTPException(status_code=403, detail="账号已被禁用")
    token = create_access_token(user.username, user.role)
    log_audit(db, user.username, "登录成功", ip=ip)
    db.commit()
    return schemas.TokenResponse(
        access_token=token, role=user.role, username=user.username
    )


@router.post("/logout")
def logout(
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    log_audit(db, user.username, "退出登录", ip=client_ip(request))
    db.commit()
    return {"msg": "已退出"}


@router.get("/me", response_model=schemas.UserOut)
def me(user: User = Depends(get_current_user)):
    return user


@router.put("/password")
def change_password(
    body: schemas.PasswordChange,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    user.password_hash = hash_password(body.new_password)
    log_audit(db, user.username, "修改密码", ip=client_ip(request))
    db.commit()
    return {"msg": "密码修改成功"}


# ---------- 用户管理（仅 admin） ----------
users_router = APIRouter(
    prefix="/api/users", tags=["users"], dependencies=[Depends(require_role("admin"))]
)


@users_router.get("", response_model=list[schemas.UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).order_by(User.id).all()


@users_router.post("", response_model=schemas.UserOut)
def create_user(
    body: schemas.UserCreate,
    request: Request,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if body.role not in ("admin", "editor", "viewer"):
        raise HTTPException(status_code=400, detail="无效的角色")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.flush()
    log_audit(db, current.username, "创建用户",
              {"target": body.username, "role": body.role}, client_ip(request))
    db.commit()
    db.refresh(user)
    return user


@users_router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    body: schemas.UserUpdate,
    request: Request,
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    changes = {}
    if body.role is not None:
        if body.role not in ("admin", "editor", "viewer"):
            raise HTTPException(status_code=400, detail="无效的角色")
        if body.role != user.role:
            changes["role"] = {"old": user.role, "new": body.role}
        user.role = body.role
    if body.is_active is not None:
        if not body.is_active:
            if user.id == current.id:
                raise HTTPException(status_code=400, detail="不能禁用自己的账号")
            if user.role == "admin":
                active_admins = (
                    db.query(User)
                    .filter(User.role == "admin", User.is_active.is_(True))
                    .count()
                )
                if active_admins <= 1:
                    raise HTTPException(status_code=400, detail="不能禁用最后一个管理员")
        if body.is_active != user.is_active:
            changes["is_active"] = {"old": user.is_active, "new": body.is_active}
        user.is_active = body.is_active
    if body.password:
        user.password_hash = hash_password(body.password)
        changes["password"] = "已重置"
    if changes:
        log_audit(db, current.username, "修改用户",
                  {"target": user.username, **changes}, client_ip(request))
    db.commit()
    db.refresh(user)
    return user
