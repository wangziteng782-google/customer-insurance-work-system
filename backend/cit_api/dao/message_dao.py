from datetime import date

from sqlalchemy import case, func, text
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
        # 新增消息同时更新last_msg_at字段，前端未读红点依赖它判断"是否有新消息"；
        # 若任务处于非进行中(1)且非进行中(修改)(10)的任何状态（含已作废8），
        # 客服发新消息即自动置为10进行中(修改)。条件放在WHERE里保证原子性。
        db.query(InsuranceTask).filter(
            InsuranceTask.task_id == dto.task_id
        ).update({
            "last_msg_at": func.now(),
            "status": case((InsuranceTask.status.notin_((1, 10)), 10), else_=InsuranceTask.status)
        }, synchronize_session=False)
        db.commit()
        db.refresh(msg)
        return msg

    @staticmethod
    def get(db: Session, message_id: int) -> ChatMessage | None:
        """按主键获取单条消息"""
        return db.get(ChatMessage, message_id)

    @staticmethod
    def recall_within_window(db: Session, message_id: int, user_id: int,
                             window_seconds: int) -> int:
        """撤回消息（逻辑删除：只打 recalled_at 标记），返回受影响行数

        时间窗判定放在 SQL 里：created_at 由数据库 now() 写入，用同一个时钟比较，
        避免应用与数据库之间的时钟/时区漂移。返回 0 表示已超时或已撤回
        （存在性、归属由上层预先校验）。

        不删行、不删七牛附件：撤回后要显示"你撤回了一条消息"，发送者还要「重新编辑」。
        也不刷新 insurance_tasks.updated_at，否则撤回一下会让任务跳到列表最前。
        """
        return (
            db.query(ChatMessage)
            .filter(
                ChatMessage.id == message_id,
                ChatMessage.user_id == user_id,
                ChatMessage.recalled_at.is_(None),
                ChatMessage.created_at
                >= func.now() - text(f"INTERVAL {window_seconds} SECOND"),
            )
            .update({"recalled_at": func.now()}, synchronize_session=False)
        )

    @staticmethod
    def refresh_last_msg_at(db: Session, task_id: str) -> None:
        """重算任务最新消息时间（排除已撤回的消息）

        撤回后 last_msg_at 不能停在已撤回的消息上，否则侧栏红点无法消除、
        任务在列表里的排序位置也回不去。
        """
        last = (
            db.query(func.max(ChatMessage.created_at))
            .filter(
                ChatMessage.task_id == task_id,
                ChatMessage.recalled_at.is_(None),
            )
            .scalar()
        )
        db.query(InsuranceTask).filter(InsuranceTask.task_id == task_id).update(
            {"last_msg_at": last}, synchronize_session=False
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
        """按 last_msg_at 升序排序"""
        return query.order_by(
            func.coalesce(InsuranceTask.last_msg_at, InsuranceTask.created_at).asc(),
            InsuranceTask.id.asc(),
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
                .filter(
                    ChatMessage.task_id.in_(task_ids),
                    ChatMessage.recalled_at.is_(None),  # 撤回的消息不计入"N 条消息"
                )
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
                InsuranceTask.last_msg_at,
            )
            .all()
        )
        companies: dict[str, dict] = {}
        for company, creator, task_id, updated_at, last_msg_at in rows:
            c = companies.setdefault(
                company,
                {"name": company, "count": 0, "users": set(), "task_times": []},
            )
            c["count"] += 1
            if creator:
                c["users"].add(creator)
            c["task_times"].append({"id": task_id, "updated_at": updated_at, "last_msg_at": last_msg_at})
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
                .filter(
                    ChatMessage.task_id.in_(task_ids),
                    ChatMessage.recalled_at.is_(None),  # 撤回的消息不计入"N 条消息"
                )
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

    # 桌面端左侧「类型筛选」的两个分组（状态码见 model.InsuranceTask.status）
    # 放在后端过滤而不是前端：列表是后端分页的（每页 10 条），前端过滤只会过滤当前这一页，
    # 页码和"还有没有下一页"都会对不上。
    STATUS_GROUP_IN_PROGRESS = (1, 2, 3, 7, 9, 10)  # 尚未递交：进行中/待确认/已做单/待补充/待递交/进行中(修改)
    STATUS_GROUP_SUBMITTED = (4, 5, 6)              # 已递交之后：已递交/对公认款中/二维码

    @staticmethod
    def list_tasks_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50,
                           status_group: str | None = None) -> list[dict]:
        """按用户获取任务列表（桌面端专用）

        status_group：
          None            → 全部，保留原有隐藏规则（隐藏非今天的已递交(4)/对公认款中(5)）
          "in_progress"   → 只留尚未递交的
          "submitted"     → 只留已递交之后的，并**跳过隐藏规则**：已递交的单基本都不是今天创建的，
                            隐藏掉的话这个筛选永远是空的（实测全库 13 条已递交，无一今天创建）
        """
        _HIDE_STATUS = (4, 5)
        _today = date.today().isoformat()
        _q = db.query(InsuranceTask).filter(InsuranceTask.user_id == user_id)
        if status_group == "in_progress":
            _q = _q.filter(InsuranceTask.status.in_(ChatMessageDAO.STATUS_GROUP_IN_PROGRESS))
        elif status_group == "submitted":
            _q = _q.filter(InsuranceTask.status.in_(ChatMessageDAO.STATUS_GROUP_SUBMITTED))
        else:
            # 隐藏条件：状态 in (4,5) 且 created_at 存在且不是今天
            # created_at 为 NULL 的任务不隐藏（兜底保留）
            _q = _q.filter(
                ~(
                    InsuranceTask.status.in_(_HIDE_STATUS)
                    & (InsuranceTask.created_at != None)
                    & (func.date(InsuranceTask.created_at) != _today)
                )
            )
        tasks = (
            ChatMessageDAO._order_by_last_message(db, _q)
            .offset(skip)
            .limit(limit)
            .all()
        )
        task_ids = [t.task_id for t in tasks]
        msg_counts: dict[str, int] = {}
        if task_ids:
            rows = (
                db.query(ChatMessage.task_id, func.count(ChatMessage.id))
                .filter(
                    ChatMessage.task_id.in_(task_ids),
                    ChatMessage.recalled_at.is_(None),  # 撤回的消息不计入"N 条消息"
                )
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
                .filter(
                    ChatMessage.task_id.in_(task_ids),
                    ChatMessage.recalled_at.is_(None),  # 撤回的消息不计入"N 条消息"
                )
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
        """获取或创建任务

        任务已存在时：只允许改写客户公司名，其余字段（保险公司/业务类型）不动。
        场景：撤回第一条消息 → 重新编辑换了一家公司 → 重发时要把任务上的客户公司一起改掉，
        否则列表里一直是旧名字。客户端平时发的是任务自身的值（相同 → 不执行更新）。
        """
        task = db.query(InsuranceTask).filter(InsuranceTask.task_id == task_id).first()
        if not task:
            task = InsuranceTask(task_id=task_id, **kwargs)
            db.add(task)
            db.commit()
            db.refresh(task)
            return task

        new_company = (kwargs.get("customer_company") or "").strip()
        if new_company and new_company != (task.customer_company or "").strip():
            task.customer_company = new_company
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
        """批量获取任务消息列表，返回 {task_id: [messages]}

        撤回的消息不进列表（列表只做展示/预览）；
        发送者要看"你撤回了一条消息"和重新编辑，走 list_by_task 的查看者逻辑。
        """
        if not task_ids:
            return {}
        messages = (
            db.query(ChatMessage)
            .filter(
                ChatMessage.task_id.in_(task_ids),
                ChatMessage.recalled_at.is_(None),
            )
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
