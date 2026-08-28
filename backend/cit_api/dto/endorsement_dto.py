from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class EndorsementCreateDTO(BaseModel):
    """客服端提交入参"""

    new_policy_id: int
    company_name: str
    job_type: Optional[str] = None
    specified_effective: Optional[bool] = False
    insurance_type: Optional[str] = None
    annual_salary: Optional[float] = None
    remarks: Optional[str] = None
    file_paths: Optional[list[str]] = None
    status: Optional[str] = "待完成"
    creator: Optional[str] = None
    handler: Optional[str] = None
    completed_at: Optional[datetime] = None


class EndorsementUpdateDTO(BaseModel):
    """编辑更新入参"""

    company_name: Optional[str] = None
    job_type: Optional[str] = None
    specified_effective: Optional[bool] = None
    insurance_type: Optional[str] = None
    annual_salary: Optional[float] = None
    remarks: Optional[str] = None
    file_paths: Optional[list[str]] = None
    status: Optional[str] = None


class EndorsementOutDTO(BaseModel):
    """返回给前端的出参"""

    id: int
    new_policy_id: int
    company_name: str
    job_type: Optional[str] = None
    specified_effective: bool
    insurance_type: Optional[str] = None
    annual_salary: Optional[float] = None
    remarks: Optional[str] = None
    file_paths: Optional[str] = None
    status: str
    creator: Optional[str] = None
    handler: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
