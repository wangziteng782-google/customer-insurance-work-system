from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChatMessageCreateDTO(BaseModel):
    """新增聊天记录入参"""
    task_id: str  # 客户端生成
    content: Optional[str] = None
    file_paths: Optional[list[str]] = None
    creator: Optional[str] = None
    user_id: Optional[int] = None
    # 首次发消息时携带，用于创建 insurance_tasks
    insurance_company: Optional[str] = None
    customer_company: Optional[str] = None
    business_type: Optional[int] = None


class ChatMessageOutDTO(BaseModel):
    """聊天记录出参"""
    id: int
    task_id: str
    content: str
    file_paths: Optional[list[str]] = None
    creator: Optional[str] = None
    creator_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatTaskOutDTO(BaseModel):
    """任务列表出参（左侧面板）"""
    task_id: str
    status: int = 0
    business_type: Optional[int] = None
    insurance_company: Optional[str] = None
    customer_company: Optional[str] = None
    creator: Optional[str] = None
    creator_name: Optional[str] = None
    user_id: Optional[int] = None
    operator: Optional[str] = None
    operator_id: Optional[int] = None
    msg_count: int = 0
    created_at: datetime
    updated_at: datetime
