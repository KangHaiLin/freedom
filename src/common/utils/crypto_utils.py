"""
加密工具类
提供密码加密、签名验证、Token生成等安全功能
"""
import hmac
import hashlib
import base64
import json
import secrets
import bcrypt
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import jwt
from pydantic import BaseSettings


class CryptoUtils:
    """加密工具类"""

    @classmethod
    def generate_hmac_signature(cls, params: Dict[str, Any], secret_key: str,
                              timestamp: int = None, nonce: str = None) -> tuple[str, int, str]:
        """生成HMAC-SHA256签名
        Args:
            params: 请求参数
            secret_key: 密钥
            timestamp: 时间戳（秒），不传则自动生成
            nonce: 随机字符串，不传则自动生成
        Returns:
            (signature, timestamp, nonce)
        """
        # 参数按字典序排序
        sorted_params = sorted(params.items(), key=lambda x: x[0])
        param_str = '&'.join([f"{k}={v}" for k, v in sorted_params])

        # 添加时间戳和随机数
        timestamp = timestamp or int(datetime.now().timestamp())
        nonce = nonce or base64.b64encode(secrets.token_bytes(16)).decode()[:8]

        sign_str = f"{param_str}&timestamp={timestamp}&nonce={nonce}"

        # 生成签名
        signature = hmac.new(
            secret_key.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).hexdigest()

        return signature, timestamp, nonce

    @classmethod
    def verify_hmac_signature(cls, signature: str, params: Dict[str, Any],
                            secret_key: str, timestamp: int, nonce: str,
                            timeout: int = 300) -> bool:
        """验证HMAC-SHA256签名
        Args:
            signature: 待验证的签名
            params: 请求参数
            secret_key: 密钥
            timestamp: 请求时间戳（秒）
            nonce: 随机字符串
            timeout: 签名有效期（秒），默认5分钟
        Returns:
            是否验证通过
        """
        # 检查时间戳是否过期
        if int(datetime.now().timestamp()) - timestamp > timeout:
            return False

        # 重新计算签名
        calculated_signature, _, _ = cls.generate_hmac_signature(params, secret_key, timestamp, nonce)
        return hmac.compare_digest(calculated_signature, signature)

    @classmethod
    def hash_password(cls, password: str, salt: Optional[bytes] = None) -> tuple[str, str]:
        """密码哈希，使用bcrypt算法
        Args:
            password: 明文密码
            salt: 可选盐值，不传则自动生成
        Returns:
            (hashed_password, salt)
        """
        if salt is None:
            salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8'), salt.decode('utf-8')

    @classmethod
    def verify_password(cls, password: str, hashed_password: str, salt: str) -> bool:
        """验证密码
        Args:
            password: 明文密码
            hashed_password: 哈希后的密码
            salt: 盐值
        Returns:
            是否匹配
        """
        calculated_hash = bcrypt.hashpw(password.encode('utf-8'), salt.encode('utf-8'))
        return hmac.compare_digest(calculated_hash, hashed_password.encode('utf-8'))

    @classmethod
    def generate_token(cls, length: int = 32) -> str:
        """生成随机Token"""
        return secrets.token_hex(length // 2)

    @classmethod
    def generate_api_key(cls) -> tuple[str, str]:
        """生成API Key和Secret"""
        api_key = f"AK{secrets.token_hex(16)}"
        api_secret = secrets.token_hex(32)
        return api_key, api_secret

    @classmethod
    def generate_jwt_token(cls, user_id: int, username: str, role: str,
                          secret_key: str, expire_minutes: int = 120) -> str:
        """生成JWT Token"""
        payload = {
            "user_id": user_id,
            "username": username,
            "role": role,
            "exp": datetime.utcnow() + timedelta(minutes=expire_minutes),
            "iat": datetime.utcnow(),
            "type": "access"
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @classmethod
    def generate_refresh_token(cls, user_id: int, secret_key: str, expire_days: int = 7) -> str:
        """生成Refresh Token"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(days=expire_days),
            "iat": datetime.utcnow(),
            "type": "refresh"
        }
        return jwt.encode(payload, secret_key, algorithm="HS256")

    @classmethod
    def verify_jwt_token(cls, token: str, secret_key: str) -> Optional[Dict]:
        """验证JWT Token
        Returns:
            验证通过返回payload，失败返回None
        """
        try:
            payload = jwt.decode(token, secret_key, algorithms=["HS256"])
            return payload
        except jwt.InvalidTokenError:
            return None

    @classmethod
    def md5(cls, data: str) -> str:
        """MD5加密"""
        return hashlib.md5(data.encode('utf-8')).hexdigest()

    @classmethod
    def sha256(cls, data: str) -> str:
        """SHA256加密"""
        return hashlib.sha256(data.encode('utf-8')).hexdigest()

    @classmethod
    def base64_encode(cls, data: str) -> str:
        """Base64编码"""
        return base64.b64encode(data.encode('utf-8')).decode('utf-8')

    @classmethod
    def base64_decode(cls, data: str) -> str:
        """Base64解码"""
        return base64.b64decode(data.encode('utf-8')).decode('utf-8')

    @classmethod
    def generate_salt(cls, length: int = 16) -> str:
        """生成随机盐值"""
        return secrets.token_hex(length // 2)

    @classmethod
    def aes_encrypt(cls, data: str, key: str) -> str:
        """AES加密（简化版，生产环境建议使用pycryptodome完整实现）"""
        from cryptography.fernet import Fernet
        # 确保key是32位url安全的base64编码
        key_bytes = cls.sha256(key).encode()[:32]
        fernet_key = base64.urlsafe_b64encode(key_bytes)
        f = Fernet(fernet_key)
        return f.encrypt(data.encode()).decode()

    @classmethod
    def aes_decrypt(cls, encrypted_data: str, key: str) -> Optional[str]:
        """AES解密"""
        try:
            from cryptography.fernet import Fernet
            key_bytes = cls.sha256(key).encode()[:32]
            fernet_key = base64.urlsafe_b64encode(key_bytes)
            f = Fernet(fernet_key)
            return f.decrypt(encrypted_data.encode()).decode()
        except:
            return None

    @classmethod
    def desensitize_data(cls, data: str, data_type: str) -> str:
        """数据脱敏
        Args:
            data: 原始数据
            data_type: 数据类型：phone/email/idcard/bankcard/name
        Returns:
            脱敏后的数据
        """
        if not data:
            return ""

        if data_type == 'phone':
            # 手机号：138****1234
            return data[:3] + "****" + data[-4:] if len(data) >= 11 else data
        elif data_type == 'email':
            # 邮箱：a****@example.com
            parts = data.split('@')
            if len(parts) == 2:
                return parts[0][:1] + "****@" + parts[1]
            return data
        elif data_type == 'idcard':
            # 身份证：1101****1234
            return data[:4] + "****" + data[-4:] if len(data) >= 18 else data
        elif data_type == 'bankcard':
            # 银行卡：6222 **** **** 1234
            return data[:4] + " **** **** " + data[-4:] if len(data) >= 16 else data
        elif data_type == 'name':
            # 姓名：张**
            return data[:1] + "**" if len(data) >= 2 else data
        else:
            # 默认中间替换为****
            if len(data) <= 4:
                return data
            half = len(data) // 2
            return data[:half-2] + "****" + data[half+2:]
