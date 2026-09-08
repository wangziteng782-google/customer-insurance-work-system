"""用户路由"""
import bcrypt
from fastapi import APIRouter, Depends, HTTPException, Form
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.model.model import User

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("")
def list_users(db: Session = Depends(get_db)):
    """获取用户列表（登录页下拉用）"""
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
    user = db.query(User).filter(User.phone == phone).first()
    if not user or not user.password:
        raise HTTPException(401, "手机号或密码错误")
    if not bcrypt.checkpw(password.encode(), user.password.encode()):
        raise HTTPException(401, "手机号或密码错误")
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
    }


@router.put("/{user_id}/password")
def change_password(
    user_id: int,
    old_password: str = Form(...),
    new_password: str = Form(...),
    db: Session = Depends(get_db),
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
