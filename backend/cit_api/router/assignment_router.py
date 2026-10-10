"""内勤负责关系（人员筛选）路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cit_api.auth import get_current_user, require_dropdown_admin
from cit_api.database import get_db
from cit_api.dto.assignment_dto import AssignmentSaveDTO
from cit_api.service.assignment_service import AssignmentService

# router 级依赖：整个模块都要求登录（写操作再叠加 require_dropdown_admin）
router = APIRouter(prefix="/api/assignments", tags=["人员筛选"],
                   dependencies=[Depends(get_current_user)])


@router.get("")
def list_assignments(db: Session = Depends(get_db)):
    """全部负责关系（登录即可；index 收窄视图和管理弹窗都用它）"""
    return AssignmentService(db).list_all()


@router.post("")
def save_assignment(
    payload: AssignmentSaveDTO,
    db: Session = Depends(get_db),
    _admin=Depends(require_dropdown_admin),
):
    """整组保存某（内勤, 保司）负责的客服（需 can_manage_dropdowns=1）"""
    return AssignmentService(db).save_group(
        payload.operator_id, payload.insurance_company, payload.user_ids
    )


@router.delete("/{operator_id}")
def delete_assignment(
    operator_id: int,
    insurance_company: str,
    db: Session = Depends(get_db),
    _admin=Depends(require_dropdown_admin),
):
    """删除某（内勤, 保司）整组负责关系（需 can_manage_dropdowns=1）"""
    return AssignmentService(db).delete_group(operator_id, insurance_company)
