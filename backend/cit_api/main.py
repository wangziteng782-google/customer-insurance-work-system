import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from cit_api.database import engine
from cit_api.model.model import Base, ChatMessage  # noqa: F401  -- 确保模型被注册
from cit_api.router.new_policy_router import router as new_policy_router
from cit_api.router.endorsement_router import router as endorsement_router
from cit_api.router.ai_router import router as ai_router
from cit_api.router.message_router import router as message_router
from cit_api.router.user_router import router as user_router

# 启动时建表（开发期使用，生产建议用 Alembic 迁移）
Base.metadata.create_all(bind=engine)

app = FastAPI(title="客服保险工单系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件服务（上传的附件）
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

app.include_router(new_policy_router)
app.include_router(endorsement_router)
app.include_router(ai_router)
app.include_router(message_router)
app.include_router(user_router)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """调试用：打印 422 时的请求体和校验错误"""
    body = await request.body()
    print(f"[422 DEBUG] {request.method} {request.url.path}")
    print(f"[422 DEBUG] body={body.decode('utf-8', errors='replace')}")
    print(f"[422 DEBUG] errors={exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})


@app.get("/")
def root():
    return {"msg": "客服保险工单系统 API 运行中"}
