"""七牛云上传工具"""
import uuid

import qiniu

from cit_api.setting import settings


def upload_bytes(data: bytes, key: str) -> str:
    """上传字节到七牛云，返回公开URL"""
    auth = qiniu.Auth(settings.QINIU_ACCESS_KEY, settings.QINIU_SECRET_KEY)
    token = auth.upload_token(settings.QINIU_BUCKET, key, 3600)
    ret, info = qiniu.put_data(token, key, data)
    if info.status_code != 200:
        raise RuntimeError(f"七牛云上传失败: {info}")
    return f"{settings.QINIU_DOMAIN}/{key}"


def upload_file(task_id: str, data: bytes, ext: str) -> str:
    """上传文件到七牛云，返回公开URL"""
    key = f"insurance/{task_id}/{uuid.uuid4().hex}{ext}"
    return upload_bytes(data, key)
