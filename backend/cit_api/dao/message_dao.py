from sqlalchemy import func, text
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
    def get(db: Session, message_id: int) -> ChatMessage | None:
        """按主键获取单条消息"""
        return db.get(ChatMessage, message_id)

    @staticmethod
    def delete_within_window(db: Session, message_id: int, user_id: int,
                             window_seconds: int) -> int:
        """撤回消息（物理删除），返回受影响行数

        时间窗判定放在 SQL 里：created_at 由数据库 now() 写入，用同一个时钟比较，
        避免应用与数据库之间的时钟/时区漂移。返回 0 表示已超出时间窗
        （存在性、归属由上层预先校验）。

        只删消息行，不刷新 insurance_tasks.updated_at，
        否则"撤回一下"会让任务跳到列表最前。
        """
        return (
            db.query(ChatMessage)
            .filter(
                ChatMessage.id == message_id,
                ChatMessage.user_id == user_id,
                ChatMessage.created_at
                >= func.now() - text(f"INTERVAL {window_seconds} SECOND"),
            )
            .delete(synchronize_session=False)
        )

    @staticmethod
    def list_by_task(db: Session, task_id: str) -> list[ChatMessage]:
        return (
            db.query(ChatMessage)
            .filter(ChatMessage.task_id == task_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    @staticmethod
    def _order_by_last_message(db: Session, query):
        """按「该任务最新一条消息的发送时间」排序（没有消息则退回任务创建时间）

        为什么不用 updated_at：内勤改状态(做单/递交/退回)会刷新 updated_at 但不新增消息，
        用 updated_at 排会导致"只改了状态的任务"也跳到新位置。
        用消息时间排序可保证：只有客服真的发了新消息，顺序才变化。
        第二排序键用 id，避免同一秒内多条任务顺序不稳定。
        """
        last_msg = (
            db.query(
                ChatMessage.task_id.label("task_id"),
                func.max(ChatMessage.created_at).label("last_msg_at"),
            )
            .group_by(ChatMessage.task_id)
            .subquery()
        )
        return (
            query.outerjoin(last_msg, last_msg.c.task_id == InsuranceTask.task_id)
            .order_by(
                func.coalesce(last_msg.c.last_msg_at, InsuranceTask.created_at).asc(),
                InsuranceTask.id.asc(),
            )
        )

    @staticmethod
    def list_tasks(db: Session, skip: int = 0, limit: int = 50) -> list[dict]:
        """获取任务列表（直接从 insurance_tasks 查）"""
        tasks = (
            ChatMessageDAO._order_by_last_message(db, db.query(InsuranceTask))
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
        """获取保险公司列表（名称 + 任务数 + 人员 + 各任务更新时间）

        task_times 是给内勤页侧栏算"未读红点"用的：红点要和浏览器里的
        seen_<任务id> 逐条比对，只返回 count 是算不出来的。
        带上它之后，侧栏 15s 轮询这个轻量接口就能刷新红点，
        不必再拉全量任务（那份数据里嵌了每个任务的消息和附件，很重）。
        """
        rows = (
            db.query(
                InsuranceTask.insurance_company,
                InsuranceTask.creator,
                InsuranceTask.task_id,
                InsuranceTask.updated_at,
            )
            .all()
        )
        companies: dict[str, dict] = {}
        for company, creator, task_id, updated_at in rows:
            c = companies.setdefault(
                company,
                {"name": company, "count": 0, "users": set(), "task_times": []},
            )
            c["count"] += 1
            if creator:
                c["users"].add(creator)
            c["task_times"].append({"id": task_id, "updated_at": updated_at})
        result = []
        for c in companies.values():
            c["users"] = list(c["users"])
            result.append(c)
        result.sort(key=lambda x: x["count"], reverse=True)
        return result

    @staticmethod
    def list_tasks_by_search(db: Session, search: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """按客户公司模糊搜索"""
        tasks = (
            db.query(InsuranceTask)
            .filter(InsuranceTask.customer_company.like(f"%{search}%"))
            .order_by(InsuranceTask.created_at.asc())
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
    def list_tasks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> list[dict]:
        """按用户获取任务列表（PySide 专用）"""
        tasks = (
            ChatMessageDAO._order_by_last_message(
                db, db.query(InsuranceTask).filter(InsuranceTask.user_id == user_id)
            )
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
    def list_tasks_by_company(db: Session, company: str, skip: int = 0, limit: int = 50) -> list[dict]:
        """按保险公司获取任务列表"""
        from sqlalchemy import func
        tasks = (
            ChatMessageDAO._order_by_last_message(
                db,
                db.query(InsuranceTask).filter(
                    InsuranceTask.insurance_company == company
                ),
            )
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
