from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class NewPolicyCreateDTO(BaseModel):
    """客服端提交入参"""

    company_name: str
    source: Optional[str] = None
    job_type: Optional[str] = None
    plan: Optional[str] = None
    is_renewal: Optional[str] = None
    specified_effective: Optional[bool] = False
    discovery_date: Optional[date] = None
    insurance_type: Optional[str] = None
    annual_salary: Optional[float] = None
    remarks: Optional[str] = None
    qualification: Optional[str] = None
    file_paths: Optional[list[str]] = None
    status: Optional[str] = "待完成"
    creator: Optional[str] = None
    handler: Optional[str] = None
    completed_at: Optional[datetime] = None


class NewPolicyUpdateDTO(BaseModel):
    """编辑更新入参"""

    company_name: Optional[str] = None
    source: Optional[str] = None
    job_type: Optional[str] = None
    plan: Optional[str] = None
    is_renewal: Optional[str] = None
    specified_effective: Optional[bool] = None
    discovery_date: Optional[date] = None
    insurance_type: Optional[str] = None
    annual_salary: Optional[float] = None
    remarks: Optional[str] = None
    qualification: Optional[str] = None
    file_paths: Optional[list[str]] = None
    status: Optional[str] = None


class NewPolicyOutDTO(BaseModel):
    """返回给前端的出参"""

    id: int
    company_name: str
    source: Optional[str] = None
    job_type: Optional[str] = None
    plan: Optional[str] = None
    is_renewal: Optional[str] = None
    specified_effective: bool
    discovery_date: Optional[date] = None
    insurance_type: Optional[str] = None
    annual_salary: Optional[float] = None
    remarks: Optional[str] = None
    qualification: Optional[str] = None
    file_paths: Optional[str] = None
    status: str
    creator: Optional[str] = None
    handler: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
