from sqlalchemy.orm import Session

from cit_api.dao.message_dao import ChatMessageDAO
from cit_api.dto.message_dto import ChatMessageCreateDTO, ChatMessageOutDTO, ChatTaskOutDTO
from cit_api.model.model import User


class ChatMessageService:
    """聊天记录业务逻辑层"""

    def __init__(self, db: Session):
        self.db = db
        self.dao = ChatMessageDAO()

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
            dto.creator_name = name_map.get(m.user_id) if m.user_id else m.creator
            result.append(dto)
        return result

    def list_tasks(self, skip: int = 0, limit: int = 50) -> list[ChatTaskOutDTO]:
        tasks = self.dao.list_tasks(self.db, skip, limit)
        user_ids = list({t['user_id'] for t in tasks if t.get('user_id')})
        name_map = self._get_user_names(user_ids)
        result = []
        for t in tasks:
            dto = ChatTaskOutDTO(**t)
            dto.creator_name = name_map.get(t.get('user_id')) if t.get('user_id') else t.get('creator')
            result.append(dto)
        return result
