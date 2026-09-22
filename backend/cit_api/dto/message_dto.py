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
    # 发送者 id：客户端判断"这条是不是我发的"要用（决定靠左/靠右、以及能否撤回）
    user_id: Optional[int] = None
    # 撤回时间：非空表示已撤回（逻辑删除，行还在）。内容只对发送者本人可见
    recalled_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskCommentDTO(BaseModel):
    """任务留言出参"""
    id: int
    task_id: str
    content: str
    author_name: Optional[str] = None
    author_id: Optional[int] = None
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
    messages: list[ChatMessageOutDTO] = []
    comments: list[TaskCommentDTO] = []

class StatusUpdateDTO(BaseModel):
    """修改状态入参"""
    status: int
    reject_reason: str | None = None
