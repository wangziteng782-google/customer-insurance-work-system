import secrets

from sqlalchemy.orm import Session

from cit_api.dao.message_dao import ChatMessageDAO
from cit_api.dto.message_dto import ChatMessageCreateDTO, ChatMessageOutDTO, ChatTaskOutDTO


def _generate_task_id() -> str:
    """生成随机任务编号，如 TK-A3F8C2"""
    return "TK-" + secrets.token_hex(3).upper()


class ChatMessageService:
    """聊天记录业务逻辑层"""

    def __init__(self, db: Session):
        self.db = db
        self.dao = ChatMessageDAO()

    def create(self, dto: ChatMessageCreateDTO) -> ChatMessageOutDTO:
        # 首次发消息（task_id 为空）→ 自动生成
        if not dto.task_id:
            dto.task_id = _generate_task_id()
        msg = self.dao.create(self.db, dto)
        return ChatMessageOutDTO.model_validate(msg)

    def list_by_task(self, task_id: str) -> list[ChatMessageOutDTO]:
        messages = self.dao.list_by_task(self.db, task_id)
        return [ChatMessageOutDTO.model_validate(m) for m in messages]

    def list_tasks(self, skip: int = 0, limit: int = 50) -> list[ChatTaskOutDTO]:
        tasks = self.dao.list_tasks(self.db, skip, limit)
        return [ChatTaskOutDTO(**t) for t in tasks]
