from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.dto.endorsement_dto import EndorsementCreateDTO, EndorsementUpdateDTO, EndorsementOutDTO
from cit_api.service.endorsement_service import EndorsementService

router = APIRouter(prefix="/api/endorsements", tags=["批改"])


@router.post("", response_model=EndorsementOutDTO)
def create_endorsement(payload: EndorsementCreateDTO, db: Session = Depends(get_db)):
    """客服端提交一条批改"""
    return EndorsementService(db).create(payload)


@router.get("", response_model=list[EndorsementOutDTO])
def list_endorsements(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """列出批改（保险端列表用）"""
    return EndorsementService(db).list_all(skip, limit)


@router.get("/{endorsement_id}", response_model=EndorsementOutDTO)
def get_endorsement(endorsement_id: int, db: Session = Depends(get_db)):
    """查看单条批改"""
    return EndorsementService(db).get_by_id(endorsement_id)


@router.put("/{endorsement_id}", response_model=EndorsementOutDTO)
def update_endorsement(endorsement_id: int, payload: EndorsementUpdateDTO, db: Session = Depends(get_db)):
    """编辑更新批改"""
    return EndorsementService(db).update(endorsement_id, payload)
