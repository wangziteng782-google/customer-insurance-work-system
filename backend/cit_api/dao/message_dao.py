from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from cit_api.model.message import ChatMessage
from cit_api.model.user import User
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
            user_id=dto.user_id,
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
            .order_by(ChatMessage.created_at.desc())
            .all()
        )

    @staticmethod
    def list_tasks(db: Session, skip: int = 0, limit: int = 50) -> list[dict]:
        """获取所有任务列表（去重，取最新消息 + 保险公司）"""
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
                ChatMessage.user_id,
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
        # 取每个任务的保险公司（任意一条有 insurance_company 的消息）
        task_ids = [r.task_id for r in results]
        company_map = {}
        if task_ids:
            company_rows = (
                db.query(
                    ChatMessage.task_id,
                    func.min(ChatMessage.insurance_company),
                )
                .filter(
                    ChatMessage.task_id.in_(task_ids),
                    ChatMessage.insurance_company.isnot(None),
                )
                .group_by(ChatMessage.task_id)
                .all()
            )
            company_map = {r[0]: r[1] for r in company_rows}

        return [
            {
                "task_id": r.task_id,
                "first_content": r.first_content[:50] if r.first_content else "",
                "creator": r.creator,
                "user_id": r.user_id,
                "created_at": r.created_at,
                "msg_count": r.msg_count,
                "insurance_company": company_map.get(r.task_id, ""),
            }
            for r in results
        ]
