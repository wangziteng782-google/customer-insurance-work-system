from sqlalchemy import func
from sqlalchemy.orm import Session

from cit_api.model.model import ChatMessage, InsuranceTask, User
from cit_api.dto.message_dto import ChatMessageCreateDTO


class ChatMessageDAO:
    """聊天记录数据访问层"""

    @staticmethod
    def create(db: Session, dto: ChatMessageCreateDTO) -> ChatMessage:
        msg = ChatMessage(
            task_id=dto.task_id,
            content=dto.content,
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
        """获取任务列表（直接从 insurance_tasks 查）"""
        tasks = (
            db.query(InsuranceTask)
            .order_by(InsuranceTask.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        # 统计每个任务的消息数
        task_ids = [t.task_id for t in tasks]
        msg_counts = {}
        if task_ids:
            rows = (
                db.query(
                    ChatMessage.task_id,
                    func.count(ChatMessage.id),
                )
                .filter(ChatMessage.task_id.in_(task_ids))
                .group_by(ChatMessage.task_id)
                .all()
            )
            msg_counts = {r[0]: r[1] for r in rows}

        return [
            {
                "task_id": t.task_id,
                "status": t.status,
                "business_type": t.business_type,
                "insurance_company": t.insurance_company,
                "customer_company": t.customer_company,
                "creator": t.creator,
                "user_id": t.user_id,
                "operator": t.operator,
                "operator_id": t.operator_id,
                "msg_count": msg_counts.get(t.task_id, 0),
                "created_at": t.created_at,
                "updated_at": t.updated_at,
            }
            for t in tasks
        ]

    @staticmethod
    def get_or_create_task(db: Session, task_id: str, **kwargs) -> InsuranceTask:
        """获取或创建任务"""
        task = db.query(InsuranceTask).filter(InsuranceTask.task_id == task_id).first()
        if not task:
            task = InsuranceTask(task_id=task_id, **kwargs)
            db.add(task)
            db.commit()
            db.refresh(task)
        return task
