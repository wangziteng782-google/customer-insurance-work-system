from sqlalchemy.orm import Session

from cit_api.dao.new_policy_dao import NewPolicyDAO
from cit_api.dto.new_policy_dto import NewPolicyCreateDTO, NewPolicyUpdateDTO, NewPolicyOutDTO


class NewPolicyService:
    """新投业务逻辑层"""

    def __init__(self, db: Session):
        self.db = db
        self.dao = NewPolicyDAO()

    def create(self, dto: NewPolicyCreateDTO) -> NewPolicyOutDTO:
        policy = self.dao.create(self.db, dto)
        return NewPolicyOutDTO.model_validate(policy)

    def list_all(self, skip: int = 0, limit: int = 100) -> list[NewPolicyOutDTO]:
        policies = self.dao.list_all(self.db, skip, limit)
        return [NewPolicyOutDTO.model_validate(p) for p in policies]

    def get_by_id(self, policy_id: int) -> NewPolicyOutDTO | None:
        policy = self.dao.get_by_id(self.db, policy_id)
        if policy is None:
            return None
        return NewPolicyOutDTO.model_validate(policy)

    def update(self, policy_id: int, dto: NewPolicyUpdateDTO) -> NewPolicyOutDTO | None:
        policy = self.dao.update(self.db, policy_id, dto.model_dump(exclude_unset=True))
        if policy is None:
            return None
        return NewPolicyOutDTO.model_validate(policy)
