from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from cit_api.model.model import User
from cit_api.database import get_db
from cit_api.setting import settings

serializer = URLSafeTimedSerializer(settings.AUTH_SECRET, salt="auth")
bearer = HTTPBearer()

def make_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db=Depends(get_db),
) -> User:
    try:
        data = serializer.loads(creds.credentials, max_age=86400)
    except (SignatureExpired, BadSignature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "登录已过期或无效")
    user = db.get(User, data["user_id"])
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return user


def require_dropdown_admin(user: User = Depends(get_current_user)):
    if not user.can_manage_dropdowns:
        raise HTTPException(403, "无权限管理下拉选项")
    return user
