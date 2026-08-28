import json

from sqlalchemy.orm import Session

from cit_api.model.endorsement_model import Endorsement
from cit_api.dto.endorsement_dto import EndorsementCreateDTO


class EndorsementDAO:
    """批改数据访问层"""

    @staticmethod
    def create(db: Session, dto: EndorsementCreateDTO) -> Endorsement:
        data = dto.model_dump()
        # file_paths: list → JSON str
        if data.get("file_paths"):
            data["file_paths"] = json.dumps(data["file_paths"], ensure_ascii=False)
        else:
            data["file_paths"] = None
        endorsement = Endorsement(**data)
        db.add(endorsement)
        db.commit()
        db.refresh(endorsement)
        return endorsement

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[Endorsement]:
        return (
            db.query(Endorsement)
            .order_by(Endorsement.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, endorsement_id: int) -> Endorsement | None:
        return db.query(Endorsement).filter(Endorsement.id == endorsement_id).first()

    @staticmethod
    def update(db: Session, endorsement_id: int, data: dict) -> Endorsement | None:
        endorsement = db.query(Endorsement).filter(Endorsement.id == endorsement_id).first()
        if endorsement is None:
            return None
        if "file_paths" in data and data["file_paths"] is not None:
            data["file_paths"] = json.dumps(data["file_paths"], ensure_ascii=False)
        for key, value in data.items():
            if value is not None:
                setattr(endorsement, key, value)
        db.commit()
        db.refresh(endorsement)
        return endorsement
