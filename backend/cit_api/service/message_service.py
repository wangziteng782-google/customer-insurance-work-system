from fastapi import HTTPException
from sqlalchemy.orm import Session

from cit_api.dao.message_dao import ChatMessageDAO
from cit_api.dto.message_dto import ChatMessageCreateDTO, ChatMessageOutDTO, ChatTaskOutDTO, TaskCommentDTO
from cit_api.model.model import InsuranceTask, User

# 允许留言的任务状态：待确认(2) / 待补充(7)
COMMENTABLE_STATUSES = (2, 7)


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

    def _get_user_names(self, user_ids: list[int]) -> dict[int, str]:
        """批量获取用户显示名"""
        if not user_ids:
            return {}
        users = self.db.query(User.id, User.display_name).filter(User.id.in_(user_ids)).all()
        return {uid: name or f"用户{uid}" for uid, name in users}

    def list_by_task(self, task_id: str) -> list[ChatMessageOutDTO]:
        messages = self.dao.list_by_task(self.db, task_id)
        user_ids = list({m.user_id for m in messages if m.user_id})
        name_map = self._get_user_names(user_ids)
        result = []
        for m in messages:
            dto = ChatMessageOutDTO.model_validate(m)
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
