from sqlalchemy.orm import Session

from cit_api.dao.endorsement_dao import EndorsementDAO
from cit_api.dto.endorsement_dto import EndorsementCreateDTO, EndorsementUpdateDTO, EndorsementOutDTO


class EndorsementService:
    """批改业务逻辑层"""

    def __init__(self, db: Session):
        self.db = db
        self.dao = EndorsementDAO()

    def create(self, dto: EndorsementCreateDTO) -> EndorsementOutDTO:
        endorsement = self.dao.create(self.db, dto)
        return EndorsementOutDTO.model_validate(endorsement)

    def list_all(self, skip: int = 0, limit: int = 100) -> list[EndorsementOutDTO]:
        endorsements = self.dao.list_all(self.db, skip, limit)
        return [EndorsementOutDTO.model_validate(e) for e in endorsements]

    def get_by_id(self, endorsement_id: int) -> EndorsementOutDTO | None:
        endorsement = self.dao.get_by_id(self.db, endorsement_id)
        if endorsement is None:
            return None
        return EndorsementOutDTO.model_validate(endorsement)

    def update(self, endorsement_id: int, dto: EndorsementUpdateDTO) -> EndorsementOutDTO | None:
        endorsement = self.dao.update(self.db, endorsement_id, dto.model_dump(exclude_unset=True))
        if endorsement is None:
            return None
        return EndorsementOutDTO.model_validate(endorsement)
