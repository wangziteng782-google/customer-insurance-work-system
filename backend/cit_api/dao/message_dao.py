from sqlalchemy import func
from sqlalchemy.orm import Session

from cit_api.model.model import ChatMessage, InsuranceTask, TaskComment, User
from cit_api.dto.message_dto import ChatMessageCreateDTO


class ChatMessageDAO:
    """聊天记录数据访问层"""

    @staticmethod
    def create(db: Session, dto: ChatMessageCreateDTO) -> ChatMessage:
        msg = ChatMessage(
            task_id=dto.task_id,
            content=dto.content or "",
            file_paths=dto.file_paths,
            creator=dto.creator,
            user_id=dto.user_id,
        )
        db.add(msg)
        # 同步刷新任务 updated_at，前端未读红点依赖它判断"是否有新消息"
        db.query(InsuranceTask).filter(
            InsuranceTask.task_id == dto.task_id
        ).update({"updated_at": func.now()}, synchronize_session=False)
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
    def list_companies(db: Session) -> list[dict]:
        """获取保险公司列表（名称 + 任务数 + 人员）"""
        from sqlalchemy import func
        tasks = (
            db.query(
                InsuranceTask.insurance_company,
                func.count(InsuranceTask.id).label("count"),
                InsuranceTask.creator,
            )
            .group_by(InsuranceTask.insurance_company, InsuranceTask.creator)
            .all()
        )
        companies: dict[str, dict] = {}
        for company, count, creator in tasks:
            if company not in companies:
                companies[company] = {"name": company, "count": 0, "users": set()}
            companies[company]["count"] += count
            if creator:
                companies[company]["users"].add(creator)
        result = []
        for c in companies.values():
            c["users"] = list(c["users"])
            result.append(c)
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    @staticmethod
    def list_tasks_by_company(db: Session, company: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """按保险公司获取任务列表"""
        from sqlalchemy import func
        tasks = (
            db.query(InsuranceTask)
            .filter(InsuranceTask.insurance_company == company)
            .order_by(InsuranceTask.updated_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        task_ids = [t.task_id for t in tasks]
        msg_counts: dict[str, int] = {}
        if task_ids:
            rows = (
                db.query(ChatMessage.task_id, func.count(ChatMessage.id))
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

    @staticmethod
    def list_comments(db: Session, task_id: str) -> list[TaskComment]:
        """获取任务留言列表"""
        return (
            db.query(TaskComment)
            .filter(TaskComment.task_id == task_id)
            .order_by(TaskComment.created_at.asc())
            .all()
        )

    @staticmethod
    def list_comments_batch(db: Session, task_ids: list[str]) -> dict[str, list[TaskComment]]:
        """批量获取任务留言列表，返回 {task_id: [comments]}"""
        if not task_ids:
            return {}
        comments = (
            db.query(TaskComment)
            .filter(TaskComment.task_id.in_(task_ids))
            .order_by(TaskComment.created_at.asc())
            .all()
        )
        result: dict[str, list[TaskComment]] = {}
        for c in comments:
            result.setdefault(c.task_id, []).append(c)
        return result

    @staticmethod
    def list_messages_batch(db: Session, task_ids: list[str]) -> dict[str, list[ChatMessage]]:
        """批量获取任务消息列表，返回 {task_id: [messages]}"""
        if not task_ids:
            return {}
        messages = (
            db.query(ChatMessage)
            .filter(ChatMessage.task_id.in_(task_ids))
            .order_by(ChatMessage.created_at.asc())
            .all()
        )
        result: dict[str, list[ChatMessage]] = {}
        for m in messages:
            result.setdefault(m.task_id, []).append(m)
        return result

    @staticmethod
    def add_comment(db: Session, task_id: str, content: str, author_name: str = None, author_id: int = None) -> TaskComment:
        """新增留言"""
        comment = TaskComment(
            task_id=task_id,
            content=content,
            author_name=author_name,
            author_id=author_id,
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)
        return comment
