"""
API依赖
"""

import logging
from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from common.config import settings
from common.utils import CryptoUtils

logger = logging.getLogger(__name__)


async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """验证API Key"""
    if not settings.API_KEY_ENABLED:
        return

    if not x_api_key or not CryptoUtils.verify_api_key(x_api_key):
        logger.warning(f"无效的API Key：{x_api_key}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的API Key")


async def get_current_user(authorization: Optional[str] = Header(None)):
    """获取当前登录用户"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的授权信息")

    token = authorization.split(" ")[1]
    try:
        payload = CryptoUtils.verify_jwt_token(token, settings.JWT_SECRET_KEY)
        if not payload:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token")
        return payload
    except Exception as e:
        logger.warning(f"JWT验证失败：{e}")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的Token") from e


async def verify_admin_role(current_user: dict = Depends(get_current_user)):
    """验证管理员权限"""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user
