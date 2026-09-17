import os

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException
from sqlalchemy.orm import Session

from cit_api.database import get_db
from cit_api.dto.message_dto import ChatMessageCreateDTO, ChatMessageOutDTO, ChatTaskOutDTO, TaskCommentDTO, StatusUpdateDTO
from cit_api.service.message_service import ChatMessageService
from cit_api.util.qiniu import upload_file
from cit_api.auth import get_current_user
from pydantic import BaseModel

router = APIRouter(prefix="/api/chat", tags=["聊天记录"], dependencies=[Depends(get_current_user)])

# 允许的扩展名
ALLOWED_EXTS = {'.png', '.jpg', '.jpeg', '.bmp', '.gif', '.webp', '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.csv'}
# 文件大小限制 10MB
MAX_FILE_SIZE = 10 * 1024 * 1024


@router.post("/messages", response_model=ChatMessageOutDTO)
def create_message(payload: ChatMessageCreateDTO, db: Session = Depends(get_db)):
    """新增一条聊天记录"""
    return ChatMessageService(db).create(payload)


@router.get("/messages", response_model=list[ChatMessageOutDTO])
def list_messages(task_id: str, db: Session = Depends(get_db)):
    """获取某任务的所有聊天记录"""
    return ChatMessageService(db).list_by_task(task_id)


@router.get("/companies")
def list_companies(db: Session = Depends(get_db)):
    """获取保险公司列表（侧栏用）"""
    return ChatMessageService(db).list_companies()


@router.get("/tasks", response_model=list[ChatTaskOutDTO])
def list_tasks(company: str = None, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """获取任务列表，可按保险公司筛选"""
    svc = ChatMessageService(db)
    if company:
        return svc.list_tasks_by_company(company, skip, limit)
    return svc.list_tasks(skip, limit)


@router.post("/upload")
async def upload_files(
    task_id: str = Form(...),
    files: list[UploadFile] = File(...),
):
    """上传附件/图片到七牛云"""
    saved_paths = []
    for file in files:
        content = await file.read()

        # 大小校验
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(400, f"文件过大：{file.filename}，最大允许 10MB")

        # 扩展名校验
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in ALLOWED_EXTS:
            raise HTTPException(400, f"不支持的文件类型：{ext}")

        # 上传到七牛云
        url = upload_file(task_id, content, ext)
        saved_paths.append(url)

    return {"file_paths": saved_paths}


@router.get("/tasks/{task_id}/comments", response_model=list[TaskCommentDTO])
def list_comments(task_id: str, db: Session = Depends(get_db)):
    """获取留言列表"""
    return ChatMessageService(db).list_comments(task_id)


@router.post("/tasks/{task_id}/comments", response_model=TaskCommentDTO)
def add_comment(
    task_id: str,
    content: str = Form(...),
    author_name: str = Form(None),
    author_id: int = Form(None),
    db: Session = Depends(get_db),
):
    """内勤新增留言"""
    return ChatMessageService(db).add_comment(task_id, content, author_name, author_id)



@router.put("/tasks/{task_id}/status")
def update_status(task_id: str, body: StatusUpdateDTO, db: Session = Depends(get_db)):
    """修改任务状态"""
    return ChatMessageService(db).update_task_status(task_id, body.status, body.reject_reason)
