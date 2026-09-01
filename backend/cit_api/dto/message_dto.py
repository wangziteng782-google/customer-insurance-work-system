from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ChatMessageCreateDTO(BaseModel):
    """新增聊天记录入参"""
    task_id: str  # 首次发消息时传空字符串，后端自动生成
    content: str
    msg_type: str = "user"  # user / system
    insurance_company: Optional[str] = None
    file_paths: Optional[list[str]] = None
    creator: Optional[str] = None
    user_id: Optional[int] = None


class ChatMessageOutDTO(BaseModel):
    """聊天记录出参"""
    id: int
    task_id: str
    content: str
    msg_type: str
    file_paths: Optional[list[str]] = None
    creator: Optional[str] = None
    creator_name: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatTaskOutDTO(BaseModel):
    """任务列表出参（左侧面板）"""
    task_id: str
    first_content: str
    msg_count: int
    insurance_company: Optional[str] = None
    creator: Optional[str] = None
    creator_name: Optional[str] = None
    created_at: datetime
