"""个人标签管理路由"""
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from cit_api.auth import get_current_user
from cit_api.database import get_db
from cit_api.service.tag_service import TagService

router = APIRouter(prefix="/api/tags", tags=["个人标签"])


@router.get("")
def list_tags(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取当前用户的所有标签"""
    return TagService(db).list_tags(user.id)


@router.post("")
def create_tag(
    name: str = Form(...),
    color: str = Form("#1677ff"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """创建标签"""
    return TagService(db).create_tag(user.id, name, color)


@router.get("/bindings")
def list_bindings(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """获取当前用户所有任务标签绑定（列表页一次拉全，避免逐任务请求）"""
    return TagService(db).list_bindings(user.id)


@router.put("/{tag_id}")
def rename_tag(
    tag_id: int,
    name: str = Form(...),
    color: str = Form(None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """修改标签名/颜色（所有任务卡片自动生效）"""
    return TagService(db).rename_tag(user.id, tag_id, name, color)


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """删除自己的标签"""
    return TagService(db).delete_tag(user.id, tag_id)


@router.get("/tasks/{task_id}")
def list_task_tags(
    task_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """获取当前用户给该任务加的标签"""
    return TagService(db).list_task_tags(user.id, task_id)


@router.post("/tasks/{task_id}")
def add_task_tag(
    task_id: str,
    tag_id: int = Form(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """给任务加标签"""
    return TagService(db).add_task_tag(user.id, task_id, tag_id)


@router.delete("/tasks/{task_id}/{tt_id}")
def delete_task_tag(
    task_id: str,
    tt_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """删除自己给该任务加的标签"""
    return TagService(db).delete_task_tag(user.id, task_id, tt_id)
