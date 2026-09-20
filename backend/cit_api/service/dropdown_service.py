from fastapi import HTTPException
from sqlalchemy.orm import Session

from cit_api.dao.dropdown_dao import DropdownDAO


class DropdownService:
    """下拉选项业务逻辑层"""

    def __init__(self, db: Session):
        self.db = db

    def list_options(self, category: str) -> list[dict]:
        opts = DropdownDAO.list_by_category(self.db, category)
        return [{"id": o.id, "value": o.value, "sort": o.sort} for o in opts]

    def add_option(self, category: str, value: str) -> dict:
        value = (value or "").strip()
        if not value:
            raise HTTPException(400, "选项值不能为空")
        exist = DropdownDAO.get_by_value(self.db, category, value)
        if exist:
            raise HTTPException(409, "该选项已存在")
        opt = DropdownDAO.add(self.db, category, value)
        return {"id": opt.id, "value": opt.value}

    def delete_option(self, category: str, opt_id: int) -> dict:
        opt = DropdownDAO.delete(self.db, category, opt_id)
        if not opt:
            raise HTTPException(404, "选项不存在")
        return {"msg": "已删除"}
