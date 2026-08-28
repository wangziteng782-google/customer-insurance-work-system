import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.dto.message_dto import ChatMessageCreateDTO, ChatMessageOutDTO, ChatTaskOutDTO
from cit_api.service.message_service import ChatMessageService

router = APIRouter(prefix="/api/chat", tags=["聊天记录"])

# 文件存储根目录
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")


@router.post("/messages", response_model=ChatMessageOutDTO)
def create_message(payload: ChatMessageCreateDTO, db: Session = Depends(get_db)):
    """新增一条聊天记录（task_id 为空时自动创建新任务）"""
    return ChatMessageService(db).create(payload)


@router.get("/messages", response_model=list[ChatMessageOutDTO])
def list_messages(task_id: str, db: Session = Depends(get_db)):
    """获取某任务的所有聊天记录"""
    return ChatMessageService(db).list_by_task(task_id)


@router.get("/tasks", response_model=list[ChatTaskOutDTO])
def list_tasks(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """获取任务列表（左侧面板）"""
    return ChatMessageService(db).list_tasks(skip, limit)


@router.post("/upload")
async def upload_files(
    task_id: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """上传附件/图片到本地"""
    task_dir = os.path.join(UPLOAD_DIR, task_id)
    os.makedirs(task_dir, exist_ok=True)

    saved_paths = []
    for file in files:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{timestamp}_{file.filename}"
        filepath = os.path.join(task_dir, filename)

        with open(filepath, "wb") as f:
            content = await file.read()
            f.write(content)

        saved_paths.append(f"uploads/{task_id}/{filename}")

    return {"file_paths": saved_paths}
