"""内勤负责关系 DTO"""
from typing import Optional

from pydantic import BaseModel


class AssignmentSaveDTO(BaseModel):
    """整组保存某（内勤, 保司）负责的客服；user_ids 为 None = 该保司下全部客服"""
    operator_id: int
    insurance_company: str
    user_ids: Optional[list[int]] = None
