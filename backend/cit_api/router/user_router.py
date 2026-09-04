"""用户路由 - 伪登录用"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.model.model import User

router = APIRouter(prefix="/api/users", tags=["用户"])


@router.get("")
def list_users(db: Session = Depends(get_db)):
    """获取所有用户列表（伪登录选择器）"""
    return db.query(User).all()
