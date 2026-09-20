"""七牛云上传工具"""
import re
import uuid
from urllib.parse import quote

import qiniu

from cit_api.setting import settings

# 文件名里不允许出现的字符：路径分隔符、控制字符、七牛 key 里的保留字符
_BAD_NAME_CHARS = re.compile(r'[\\/:*?"<>|\x00-\x1f]')


def _safe_name(filename: str, ext: str) -> str:
    """把上传时的原始文件名整理成能当七牛 key 用的名字

    - 只取最后一段（防止 ../../ 之类构造出越权 key）
    - 去掉分隔符与控制字符
    - 去掉自带扩展名，避免出现 报表.pdf.pdf
    - 限长 60 字符；无可用名字时退回随机串
    """
    name = str(filename or "").replace("\\", "/").split("/")[-1].strip()
    name = _BAD_NAME_CHARS.sub("", name)
    if ext and name.lower().endswith(ext.lower()):
        name = name[: -len(ext)]
    name = name.strip()[:60].strip()
    return name or uuid.uuid4().hex[:8]


def upload_bytes(data: bytes, key: str) -> str:
    """上传字节到七牛云，返回公开URL"""
    auth = qiniu.Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    token = auth.upload_token(settings.QINIU_BUCKET, key, 3600)
    ret, info = qiniu.put_data(token, key, data)
    if info.status_code != 200:
        raise RuntimeError(f"七牛云上传失败: {info}")
    # key 里会有中文/空格，URL 必须转义（safe="/" 保留目录层级）
    return f"{settings.QINIU_DOMAIN}/{quote(key, safe='/')}"


def upload_file(task_id: str, data: bytes, ext: str, filename: str = "") -> str:
    """上传文件到七牛云，返回公开URL

    key = insurance/{任务号}/{随机段}/{原文件名}：
    - 文件名保持原样，消息里的附件名、下载到本地的文件名都是原名
    - 随机段放在目录上而不是文件名上，既保证同名文件不互相覆盖
      （key 相同七牛会覆盖，会让旧消息的附件指向新文件），
      又不会让界面上出现 -a1b2c3 这种尾巴
    """
    key = f"insurance/{task_id}/{uuid.uuid4().hex[:6]}/{_safe_name(filename, ext)}{ext}"
    return upload_bytes(data, key)
