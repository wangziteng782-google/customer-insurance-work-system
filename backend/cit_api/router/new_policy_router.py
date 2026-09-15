from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.dto.new_policy_dto import NewPolicyCreateDTO, NewPolicyUpdateDTO, NewPolicyOutDTO
from cit_api.service.new_policy_service import NewPolicyService
from cit_api.auth import get_current_user

router = APIRouter(prefix="/api/new-policies", tags=["新投"], dependencies=[Depends(get_current_user)])


@router.post("", response_model=NewPolicyOutDTO)
def create_new_policy(payload: NewPolicyCreateDTO, db: Session = Depends(get_db)):
    """客服端提交一条新投"""
    return NewPolicyService(db).create(payload)


@router.get("", response_model=list[NewPolicyOutDTO])
def list_new_policies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """列出新投（保险端列表用）"""
    return NewPolicyService(db).list_all(skip, limit)


@router.get("/{policy_id}", response_model=NewPolicyOutDTO)
def get_new_policy(policy_id: int, db: Session = Depends(get_db)):
    """查看单条新投"""
    svc = NewPolicyService(db)
    policy = svc.get_by_id(policy_id)
    if policy is None:
        raise HTTPException(404, "新投不存在")
    return policy


@router.put("/{policy_id}", response_model=NewPolicyOutDTO)
def update_new_policy(policy_id: int, payload: NewPolicyUpdateDTO, db: Session = Depends(get_db)):
    """编辑更新新投"""
    svc = NewPolicyService(db)
    policy = svc.update(policy_id, payload)
    if policy is None:
        raise HTTPException(404, "新投不存在")
    return policy
