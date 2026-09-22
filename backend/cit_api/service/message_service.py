from fastapi import HTTPException
from sqlalchemy.orm import Session

from cit_api.dao.message_dao import ChatMessageDAO
from cit_api.dto.message_dto import ChatMessageCreateDTO, ChatMessageOutDTO, ChatTaskOutDTO, TaskCommentDTO
from cit_api.model.model import InsuranceTask, User

# 允许留言的任务状态：待确认(2) / 待补充(7)
COMMENTABLE_STATUSES = (2, 7)

# 撤回时间窗（秒）：发送后超过该时长不可撤回（对齐微信的 2 分钟）
RECALL_WINDOW_SECONDS = 120


class ChatMessageService:
    """聊天记录业务逻辑层"""

    def __init__(self, db: Session):
        self.db = db
        self.dao = ChatMessageDAO()

    def _get_task_or_404(self, task_id: str) -> InsuranceTask:
        """获取任务，不存在则 404"""
        task = self.db.query(InsuranceTask).filter(InsuranceTask.task_id == task_id).first()
        if not task:
            raise HTTPException(404, "任务不存在")
        return task

    def create(self, dto: ChatMessageCreateDTO) -> ChatMessageOutDTO:
        # 首次发消息时创建 insurance_tasks 记录
        self.dao.get_or_create_task(
            self.db,
            task_id=dto.task_id,
            insurance_company=dto.insurance_company,
            customer_company=dto.customer_company,
            business_type=dto.business_type,
            creator=dto.creator,
            user_id=dto.user_id,
        )
        msg = self.dao.create(self.db, dto)
        return ChatMessageOutDTO.model_validate(msg)

    def recall(self, message_id: int, user: User) -> dict:
        """撤回消息：仅限本人发送、且发送未超过 RECALL_WINDOW_SECONDS

        逻辑删除：只写 recalled_at，消息行保留 —— 客户端要显示"你撤回了一条消息"，
        发送者还要能「重新编辑」把内容放回输入框。
        撤回的内容只对发送者可见（见 list_by_task），别人只看到"撤回了"这个事实。
        """
        msg = self.dao.get(self.db, message_id)
        if not msg:
            raise HTTPException(404, "消息不存在")
        if msg.user_id != user.id:
            # 带上真正的发送者：下次出现这句时一眼能看出是谁发的，不用再猜
            sender = msg.creator or f"用户{msg.user_id}"
            raise HTTPException(403, f"该消息由 {sender} 发送，只能撤回自己发送的消息")
        if msg.recalled_at:
            raise HTTPException(400, "该消息已撤回")

        task_id = msg.task_id
        # 时间窗判定与打标记在同一条 SQL 内完成，避免"查完再改"的竞态
        updated = self.dao.recall_within_window(
            self.db, message_id, user.id, RECALL_WINDOW_SECONDS
        )
        if updated:
            # 撤回成功：重算 last_msg_at（排除撤回消息），与撤回标记同一个 commit
            self.dao.refresh_last_msg_at(self.db, task_id)
        self.db.commit()
        if not updated:
            raise HTTPException(403, "超过 2 分钟，无法撤回")
        return {"id": message_id, "task_id": task_id, "recalled": True}

    def _get_user_names(self, user_ids: list[int]) -> dict[int, str]:
        """批量获取用户显示名"""
        if not user_ids:
            return {}
        users = self.db.query(User.id, User.display_name).filter(User.id.in_(user_ids)).all()
        return {uid: name or f"用户{uid}" for uid, name in users}

    def list_by_task(self, task_id: str, viewer_id: int | None = None) -> list[ChatMessageOutDTO]:
        """某任务的全部聊天记录

        viewer_id = 当前请求者：撤回过的消息仍然返回（客户端要渲染撤回提示），
        但内容与附件只给发送者本人（他要「重新编辑」），其他人拿到空内容。
        """
        messages = self.dao.list_by_task(self.db, task_id)
        user_ids = list({m.user_id for m in messages if m.user_id})
        name_map = self._get_user_names(user_ids)
        result = []
        for m in messages:
            dto = ChatMessageOutDTO.model_validate(m)
            if m.recalled_at and m.user_id != viewer_id:
                dto.content = ""
                dto.file_paths = None
            dto.creator_name = name_map.get(m.user_id) or m.creator
            result.append(dto)
        return result

    def list_tasks(self, skip: int = 0, limit: int = 50) -> list[ChatTaskOutDTO]:
        tasks = self.dao.list_tasks(self.db, skip, limit)
        task_ids = [t['task_id'] for t in tasks]
        msg_map = self.dao.list_messages_batch(self.db, task_ids)
        comment_map = self.dao.list_comments_batch(self.db, task_ids)
        user_ids = list({t['user_id'] for t in tasks if t.get('user_id')})
        name_map = self._get_user_names(user_ids)
        result = []
        for t in tasks:
            dto = ChatTaskOutDTO(**t)
            dto.creator_name = name_map.get(t.get('user_id')) or t.get('creator')
            dto.messages = [ChatMessageOutDTO.model_validate(m) for m in msg_map.get(t['task_id'], [])]
            dto.comments = [TaskCommentDTO.model_validate(c) for c in comment_map.get(t['task_id'], [])]
            result.append(dto)
        return result

    def list_companies(self) -> list[dict]:
        """获取保险公司列表（侧栏用）"""
        return self.dao.list_companies(self.db)

    def list_tasks_by_search(self, search: str, skip: int = 0, limit: int = 50) -> list[ChatTaskOutDTO]:
        """按客户公司模糊搜索"""
        tasks = self.dao.list_tasks_by_search(self.db, search, skip, limit)
        task_ids = [t['task_id'] for t in tasks]
        msg_map = self.dao.list_messages_batch(self.db, task_ids)
        comment_map = self.dao.list_comments_batch(self.db, task_ids)
        user_ids = list({t['user_id'] for t in tasks if t.get('user_id')})
        name_map = self._get_user_names(user_ids)
        result = []
        for t in tasks:
            dto = ChatTaskOutDTO(**t)
            dto.creator_name = name_map.get(t.get('user_id')) or t.get('creator')
            dto.messages = [ChatMessageOutDTO.model_validate(m) for m in msg_map.get(t['task_id'], [])]
            dto.comments = [TaskCommentDTO.model_validate(c) for c in comment_map.get(t['task_id'], [])]
            result.append(dto)
        return result

    def list_tasks_by_user(self, user_id: int, skip: int = 0, limit: int = 50) -> list[ChatTaskOutDTO]:
        """按用户获取任务列表（PySide 专用）"""
        tasks = self.dao.list_tasks_by_user(self.db, user_id, skip, limit)
        task_ids = [t['task_id'] for t in tasks]
        msg_map = self.dao.list_messages_batch(self.db, task_ids)
        comment_map = self.dao.list_comments_batch(self.db, task_ids)
        user_ids = list({t['user_id'] for t in tasks if t.get('user_id')})
        name_map = self._get_user_names(user_ids)
        result = []
        for t in tasks:
            dto = ChatTaskOutDTO(**t)
            dto.creator_name = name_map.get(t.get('user_id')) or t.get('creator')
            dto.messages = [ChatMessageOutDTO.model_validate(m) for m in msg_map.get(t['task_id'], [])]
            dto.comments = [TaskCommentDTO.model_validate(c) for c in comment_map.get(t['task_id'], [])]
            result.append(dto)
        return result

    def list_tasks_by_company(self, company: str, skip: int = 0, limit: int = 50) -> list[ChatTaskOutDTO]:
        """按保险公司获取任务列表（含嵌入的 messages 和 comments）"""
        tasks = self.dao.list_tasks_by_company(self.db, company, skip, limit)
        task_ids = [t['task_id'] for t in tasks]
        msg_map = self.dao.list_messages_batch(self.db, task_ids)
        comment_map = self.dao.list_comments_batch(self.db, task_ids)
        user_ids = list({t['user_id'] for t in tasks if t.get('user_id')})
        name_map = self._get_user_names(user_ids)
        result = []
        for t in tasks:
            dto = ChatTaskOutDTO(**t)
            dto.creator_name = name_map.get(t.get('user_id')) or t.get('creator')
            dto.messages = [ChatMessageOutDTO.model_validate(m) for m in msg_map.get(t['task_id'], [])]
            dto.comments = [TaskCommentDTO.model_validate(c) for c in comment_map.get(t['task_id'], [])]
            result.append(dto)
        return result

    def list_comments(self, task_id: str) -> list[TaskCommentDTO]:
        """获取留言列表 — 仅待确认(2)/待补充(7)状态返回"""
        task = self._get_task_or_404(task_id)
        if task.status not in COMMENTABLE_STATUSES:
            return []
        comments = self.dao.list_comments(self.db, task_id)
        return [TaskCommentDTO.model_validate(c) for c in comments]

    def add_comment(self, task_id: str, content: str, author_name: str = None, author_id: int = None) -> TaskCommentDTO:
        """内勤新增留言"""
        if not content or not content.strip():
            raise HTTPException(400, "留言内容不能为空")
        task = self._get_task_or_404(task_id)
        if task.status not in COMMENTABLE_STATUSES:
            raise HTTPException(409, "当前任务状态不允许留言")
        comment = self.dao.add_comment(self.db, task_id, content, author_name, author_id)
        return TaskCommentDTO.model_validate(comment)

    def update_task_status(self, task_id: str, status: int, reject_reason: str = None) -> dict:
        """修改任务状态"""
        if status < 1 or status > 9:
            raise HTTPException(400, "状态值无效")
        task = self._get_task_or_404(task_id)
        # 已作废不可变更
        if task.status == 8:
            raise HTTPException(400, "已作废任务不可变更")
        # 退回状态必须填写原因
        if status in COMMENTABLE_STATUSES and not (reject_reason and reject_reason.strip()):
            raise HTTPException(400, "退回操作必须填写原因")
        # 幂等：相同状态跳过
        if task.status == status:
            return {"task_id": task_id, "status": status}
        task.status = status
        # 退回原因写入留言表
        if status in COMMENTABLE_STATUSES and reject_reason:
            self.dao.add_comment(self.db, task_id, reject_reason.strip(), author_name=None, author_id=None)
        self.db.commit()
        return {"task_id": task_id, "status": status}
