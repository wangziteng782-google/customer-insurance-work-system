from fastapi import HTTPException
from sqlalchemy.orm import Session

from cit_api.dao.assignment_dao import AssignmentDAO
from cit_api.model.model import User


class AssignmentService:
    """内勤负责关系业务层"""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[dict]:
        return [_row(r) for r in AssignmentDAO.list_all(self.db)]

    def save_group(self, operator_id: int, insurance_company: str, user_ids: list[int] | None) -> list[dict]:
        """整组保存（新增 = 编辑，同一个入口）。user_ids 为 None = 该保司下全部客服。
        姓名冗余列由这里从 users 表回填——前端只传 id。"""
        insurance_company = (insurance_company or "").strip()
        if not insurance_company:
            raise HTTPException(400, "保险公司不能为空")
        operator = self.db.query(User).filter(User.id == operator_id).first()
        if not operator or operator.role not in (2, 22):
            raise HTTPException(400, "内勤不存在或角色不符")
        if user_ids is not None:
            if not user_ids:
                raise HTTPException(400, "请选择客服，或勾选「全部」")
            users = self.db.query(User).filter(User.id.in_(user_ids)).all()
            if len(users) != len(set(user_ids)):
                raise HTTPException(400, "存在无效的客服")
            if any(u.role not in (1, 11) for u in users):
                raise HTTPException(400, "所选用户不是客服角色")
            members = [(u.id, u.display_name or u.username) for u in users]
        else:
            members = None
        rows = AssignmentDAO.replace_group(
            self.db, operator_id, operator.display_name or operator.username, insurance_company, members
        )
        return [_row(r) for r in rows]

    def delete_group(self, operator_id: int, insurance_company: str) -> dict:
        deleted = AssignmentDAO.delete_group(self.db, operator_id, insurance_company)
        if not deleted:
            raise HTTPException(404, "该负责关系不存在")
        return {"msg": "已删除"}


def _row(r) -> dict:
    return {
        "id": r.id,
        "operator_id": r.operator_id,
        "operator_name": r.operator_name,
        "insurance_company": r.insurance_company,
        "user_id": r.user_id,
        "user_name": r.user_name,
    }
