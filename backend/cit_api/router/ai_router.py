"""AI 识别路由"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.service.qwen_service import extract_insurance_info
from cit_api.service.message_service import ChatMessageService

router = APIRouter(prefix="/api/ai", tags=["AI识别"])


@router.post("/recognize")
def ai_recognize(request: dict):
    """AI 识别客户信息

    请求体：{"text": "客户对话文本"}
    返回：{"company_name": "XX公司", "insurance_type": "意外险", ...}
    """
    text = request.get("text", "")
    if not text:
        return {}

    result = extract_insurance_info(text)
    return result


@router.post("/extract")
def ai_extract(task_id: str, db: Session = Depends(get_db)):
    """从任务聊天消息中提取保险信息

    参数：task_id
    返回：{"company_name": "XX公司", "insurance_type": "意外险", ...}
    """
    messages = ChatMessageService(db).list_by_task(task_id)
    text = "\n".join([m.content for m in messages if m.content])
    if not text:
        return {}

    result = extract_insurance_info(text)
    return result
