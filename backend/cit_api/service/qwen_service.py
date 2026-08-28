"""千问 AI 识别服务 - 从客户文本中提取保险信息"""
import json
import requests

from cit_api.setting import settings


# 提取字段的提示词
EXTRACT_PROMPT = """你是一个保险客服助手。请从以下客户对话/文本中提取保险相关信息，返回 JSON 格式。

需要提取的字段：
- company_name: 公司名称（如有）
- job_type: 工种（如：电工、焊工、建筑工人等）
- insurance_type: 险种（如：意外险、医疗险、重疾险等）
- annual_salary: 年薪（数字，单位：万元）
- source: 来源（如：电话、微信、官网等）
- plan: 方案（如：方案A、基础版等）
- is_renewal: 续保/新投（"续保" 或 "新投"）
- discovery_date: 发现日期（格式：YYYY-MM-DD）
- qualification: 资质（如：一级资质、特种作业证等）
- specified_effective: 是否指定生效（true/false）
- remarks: 备注（其他重要信息）

只返回 JSON，不要其他内容。如果某个字段未提及，不要包含在 JSON 中。

客户文本：
{text}
"""


def extract_insurance_info(text: str) -> dict:
    """调用千问 AI 提取保险信息

    Args:
        text: 客户对话/文本内容

    Returns:
        提取的字段 dict，例如：
        {"company_name": "XX公司", "insurance_type": "意外险"}
    """
    if not text or not text.strip():
        return {}

    prompt = EXTRACT_PROMPT.format(text=text)

    payload = {
        "model": settings.QWEN_MODEL,
        "input": {
            "messages": [
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {
            "result_format": "message",
            "temperature": 0.3,  # 低温度，更精确
            "max_tokens": 1000
        }
    }

    headers = {
        "Authorization": f"Bearer {settings.QWEN_API_KEY}",
        "Content-Type": "application/json"
    }

    try:
        resp = requests.post(
            settings.QWEN_API_URL,
            json=payload,
            headers=headers,
            timeout=30
        )
        resp.raise_for_status()

        result = resp.json()
        # 解析千问返回的内容
        content = result.get("output", {}).get("choices", [{}])[0].get("message", {}).get("content", "")

        if not content:
            return {}

        # 尝试解析 JSON（可能包裹在 ```json ``` 中）
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        extracted = json.loads(content)
        return extracted if isinstance(extracted, dict) else {}

    except json.JSONDecodeError:
        # JSON 解析失败，尝试正则提取
        return {}
    except Exception as e:
        print(f"千问 AI 调用失败: {e}")
        return {}
