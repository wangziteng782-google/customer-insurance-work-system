import json

from sqlalchemy.orm import Session

from cit_api.model.new_policy_model import NewPolicy
from cit_api.dto.new_policy_dto import NewPolicyCreateDTO


class NewPolicyDAO:
    """新投数据访问层"""

    @staticmethod
    def create(db: Session, dto: NewPolicyCreateDTO) -> NewPolicy:
        data = dto.model_dump()
        # file_paths: list → JSON str
        if data.get("file_paths"):
            data["file_paths"] = json.dumps(data["file_paths"], ensure_ascii=False)
        else:
            data["file_paths"] = None
        policy = NewPolicy(**data)
        db.add(policy)
        db.commit()
        db.refresh(policy)
        return policy

    @staticmethod
    def list_all(db: Session, skip: int = 0, limit: int = 100) -> list[NewPolicy]:
        return (
            db.query(NewPolicy)
            .order_by(NewPolicy.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_by_id(db: Session, policy_id: int) -> NewPolicy | None:
        return db.query(NewPolicy).filter(NewPolicy.id == policy_id).first()

    @staticmethod
    def update(db: Session, policy_id: int, data: dict) -> NewPolicy | None:
        policy = db.query(NewPolicy).filter(NewPolicy.id == policy_id).first()
        if policy is None:
            return None
        # file_paths: list → JSON str
        if "file_paths" in data and data["file_paths"] is not None:
            data["file_paths"] = json.dumps(data["file_paths"], ensure_ascii=False)
        for key, value in data.items():
            if value is not None:
                setattr(policy, key, value)
        db.commit()
        db.refresh(policy)
        return policy
