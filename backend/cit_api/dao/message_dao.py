from sqlalchemy import func
from sqlalchemy.orm import Session

from cit_api.model.message import ChatMessage
from cit_api.dto.message_dto import ChatMessageCreateDTO


class ChatMessageDAO:
    """聊天记录数据访问层"""

    @staticmethod
    def create(db: Session, dto: ChatMessageCreateDTO) -> ChatMessage:
        msg = ChatMessage(
            task_id=dto.task_id,
            content=dto.content,
            msg_type=dto.msg_type,
            insurance_company=dto.insurance_company,
            file_paths=dto.file_paths,
            creator=dto.creator,
        )
        db.add(msg)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def list_by_task(db: Session, task_id: str) -> list[ChatMessage]:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.task_id == task_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    @staticmethod
    def list_tasks(db: Session, skip: int = 0, limit: int = 50) -> list[dict]:
        """获取所有任务列表（去重，取最新消息）"""
        subq = (
            db.query(
                ChatMessage.task_id,
                func.count(ChatMessage.id).label("msg_count"),
                func.max(ChatMessage.created_at).label("latest_at"),
            )
            .group_by(ChatMessage.task_id)
            .subquery()
        )
        results = (
            db.query(
                ChatMessage.task_id,
                ChatMessage.content.label("first_content"),
                ChatMessage.creator,
                ChatMessage.created_at,
                subq.c.msg_count,
            )
            .join(subq, ChatMessage.task_id == subq.c.task_id)
            .filter(ChatMessage.created_at == subq.c.latest_at)
            .order_by(subq.c.latest_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [
            {
                "task_id": r.task_id,
                "first_content": r.first_content[:50] if r.first_content else "",
                "creator": r.creator,
                "created_at": r.created_at,
                "msg_count": r.msg_count,
            }
            for r in results
        ]
