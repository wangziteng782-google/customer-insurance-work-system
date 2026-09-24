"""OCR 身份证识别路由"""
from fastapi import APIRouter, Depends, HTTPException
from cit_api.auth import get_current_user
from cit_api.service.ocr_service import recognize_id_card, recognize_raw, verify_id_card

router = APIRouter(prefix="/api/ocr", tags=["OCR识别"])


@router.post("/recognize")
def ocr_recognize(request: dict):
    """OCR 识别身份证

    请求体：{"image_urls": ["https://...", ...]}
    返回：{"results": [{name, id_number, valid, birth_date, gender, age, area}, ...]}
    """
    urls = request.get("image_urls", [])
    if not urls:
        raise HTTPException(400, "缺少图片URL (image_urls)")

    results = []
    errors = []
    for i, url in enumerate(urls):
        data, error = recognize_id_card(url)
        if error:
            errors.append({"index": i, "url": url, "error": error})
            results.append(None)
        else:
            results.append(data)

    return {"results": results, "errors": errors}


@router.post("/recognize_raw")
def ocr_recognize_raw(request: dict):
    """OCR 原样输出（不做身份证字段提取）

    请求体：{"image_urls": ["https://...", ...]}
    返回：{"results": [{"text": "原文"} 或 None, ...], "errors": [...]}
    """
    urls = request.get("image_urls", [])
    if not urls:
        raise HTTPException(400, "缺少图片URL (image_urls)")

    results = []
    errors = []
    for i, url in enumerate(urls):
        data, error = recognize_raw(url)
        if error:
            errors.append({"index": i, "url": url, "error": error})
            results.append(None)
        else:
            results.append(data)

    return {"results": results, "errors": errors}


@router.post("/verify")
def ocr_verify(request: dict):
    """身份证校验 — 完全复刻 Umi-OCR 校验逻辑

    请求体：{"name": "张三", "id_number": "13043120030122123X"}
    返回：{name, id_card, id_type, area, birth_date, age, gender, correct_check_code, is_valid, warnings, errors}
    """
    name = request.get("name", "")
    id_number = request.get("id_number", "")
    if not id_number:
        raise HTTPException(400, "缺少身份证号 (id_number)")

    result = verify_id_card(name, id_number)
    return result
