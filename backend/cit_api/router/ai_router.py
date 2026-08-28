"""AI 识别路由"""
from fastapi import APIRouter

from cit_api.service.qwen_service import extract_insurance_info

router = APIRouter(prefix="/api/ai", tags=["AI识别"])


class AiRecognizeRequest:
    """AI 识别请求"""
    text: str


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
