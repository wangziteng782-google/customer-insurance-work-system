"""用户路由"""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.model.model import User
from cit_api.auth import make_token, get_current_user

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("", dependencies=[Depends(get_current_user)])
def list_users(db: Session = Depends(get_db)):
    """获取用户列表（需要登录）"""
    users = db.query(User).all()
    return [
        {"id": u.id, "username": u.username, "display_name": u.display_name, "role": u.role}
        for u in users
    ]


@router.post("/login")
def login(
    phone: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    """登录验证（手机号 + 密码）"""
    # 空参数直接返回 401,避免 bcrypt 在空字符串上抛 ValueError
    if not phone or not phone.strip() or not password:
        raise HTTPException(401, "手机号或密码错误")
    user = db.query(User).filter(User.phone == phone).first()
    if not user or not user.password:
        raise HTTPException(401, "手机号或密码错误")
    try:
        if not bcrypt.checkpw(password.encode(), user.password.encode()):
            raise HTTPException(401, "手机号或密码错误")
    except (ValueError, TypeError):
        raise HTTPException(401, "手机号或密码错误")
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
        "token": make_token(user.id),
    }


@router.put("/{user_id}/password")
def change_password(
    user_id: int,
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
    me: User = Depends(get_current_user),
):
    """修改密码"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    if not bcrypt.checkpw(old_password.encode(), user.password.encode()):
        raise HTTPException(401, "原密码错误")
    if len(new_password) < 6:
        raise HTTPException(400, "新密码至少6位")
    user.password = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt(10)).decode()
    db.commit()
    return {"msg": "密码修改成功"}
