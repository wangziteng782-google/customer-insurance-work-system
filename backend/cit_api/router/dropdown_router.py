"""下拉选项管理路由"""
from fastapi import APIRouter, Depends, Form
from sqlalchemy.orm import Session

from cit_api.auth import get_current_user, require_dropdown_admin
from cit_api.database import get_db
from cit_api.service.dropdown_service import DropdownService

# router 级依赖：整个模块都要求登录（写操作再叠加 require_dropdown_admin）
router = APIRouter(prefix="/api/dropdowns", tags=["下拉选项管理"],
                   dependencies=[Depends(get_current_user)])


@router.get("/{category}")
def list_options(category: str, db: Session = Depends(get_db)):
    """获取某分类的所有选项（登录即可）"""
    return DropdownService(db).list_options(category)


@router.post("/{category}")
def add_option(category: str, value: str = Form(...), db: Session = Depends(get_db),
               _admin=Depends(require_dropdown_admin)):
    """新增选项（需 can_manage_dropdowns=1）"""
    return DropdownService(db).add_option(category, value)


@router.delete("/{category}/{opt_id}")
def delete_option(category: str, opt_id: int, db: Session = Depends(get_db),
                  _admin=Depends(require_dropdown_admin)):
    """删除选项（需 can_manage_dropdowns=1）"""
    return DropdownService(db).delete_option(category, opt_id)
