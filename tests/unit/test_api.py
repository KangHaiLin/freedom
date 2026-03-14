"""
API模块单元测试
"""
import pytest
from fastapi.testclient import TestClient
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import jwt
import json

from user_interface.backend.main import app
from user_interface.backend.dependencies import get_api_key, get_current_user, get_current_admin
from common.config.settings import settings


client = TestClient(app)


def test_api_health_check():
    """测试健康检查接口"""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "version" in data
    assert "timestamp" in data


def test_api_docs():
    """测试API文档访问"""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "Swagger UI" in response.text

    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["openapi"] == "3.1.0"


class TestMarketDataAPI:
    """行情数据API测试"""

    @patch('user_interface.backend.routers.market.query_manager')
    def test_get_realtime_quote(self, mock_query_manager):
        """测试获取实时行情接口"""
        # 模拟返回数据
        mock_result = Mock()
        mock_result.success = True
        mock_result.data.to_dict.return_value = [{
            "stock_code": "000001.SZ",
            "price": 10.0,
            "volume": 1000,
            "time": datetime.now().isoformat()
        }]
        mock_query_manager.execute_query.return_value = mock_result

        # 构造请求头
        headers = {"X-API-Key": settings.API_KEYS[0]}

        response = client.get(
            "/api/v1/market/realtime?stock_codes=000001.SZ,600000.SH",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 1
        assert data["data"][0]["stock_code"] == "000001.SZ"

    @patch('user_interface.backend.routers.market.query_manager')
    def test_get_daily_quote(self, mock_query_manager):
        """测试获取日线行情接口"""
        mock_result = Mock()
        mock_result.success = True
        mock_result.data.to_dict.return_value = [{
            "trade_date": "2023-01-01",
            "open": 10.0,
            "high": 10.5,
            "low": 9.5,
            "close": 10.2,
            "volume": 100000
        }]
        mock_query_manager.execute_query.return_value = mock_result

        headers = {"X-API-Key": settings.API_KEYS[0]}
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")

        response = client.get(
            f"/api/v1/market/daily/000001.SZ?start_date={start_date}&end_date={end_date}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert len(data["data"]) == 1
        assert data["data"][0]["close"] == 10.2


class TestFundamentalDataAPI:
    """基本面数据API测试"""

    @patch('user_interface.backend.routers.fundamental.query_manager')
    def test_get_financial_indicators(self, mock_query_manager):
        """测试获取财务指标接口"""
        mock_result = Mock()
        mock_result.success = True
        mock_result.data.to_dict.return_value = [{
            "stock_code": "000001.SZ",
            "pe": 10.5,
            "pb": 1.2,
            "roe": 15.3,
            "market_cap": 100000000000
        }]
        mock_query_manager.execute_query.return_value = mock_result

        headers = {"X-API-Key": settings.API_KEYS[0]}
        response = client.get(
            "/api/v1/fundamental/indicators?stock_codes=000001.SZ",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"][0]["pe"] == 10.5
        assert data["data"][0]["roe"] == 15.3


class TestAuthenticationAPI:
    """认证API测试"""

    def test_invalid_api_key(self):
        """测试无效API Key"""
        headers = {"X-API-Key": "invalid_key"}
        response = client.get("/api/v1/market/realtime?stock_codes=000001.SZ", headers=headers)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API Key"

    def test_missing_api_key(self):
        """测试缺失API Key"""
        response = client.get("/api/v1/market/realtime?stock_codes=000001.SZ")
        assert response.status_code == 401
        assert response.json()["detail"] == "X-API-Key header missing"

    def test_login_success(self):
        """测试登录成功"""
        with patch('user_interface.backend.routers.system.CryptoUtils.verify_password') as mock_verify:
            mock_verify.return_value = True

            response = client.post(
                "/api/v1/system/login",
                json={"username": "admin", "password": "admin123"}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["code"] == 0
            assert "access_token" in data["data"]
            assert data["data"]["token_type"] == "bearer"

    def test_login_failure(self):
        """测试登录失败"""
        with patch('user_interface.backend.routers.system.CryptoUtils.verify_password') as mock_verify:
            mock_verify.return_value = False

            response = client.post(
                "/api/v1/system/login",
                json={"username": "admin", "password": "wrongpass"}
            )
            assert response.status_code == 401
            assert response.json()["detail"] == "Incorrect username or password"


class TestJWTAuthentication:
    """JWT认证测试"""

    def test_get_current_user_valid_token(self):
        """测试有效JWT令牌"""
        payload = {
            "sub": "admin",
            "user_id": 1,
            "role": "user",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        from user_interface.backend.dependencies import oauth2_scheme
        with patch('user_interface.backend.dependencies.oauth2_scheme') as mock_scheme:
            mock_scheme.return_value = token
            user = get_current_user(token)
            assert user["username"] == "admin"
            assert user["user_id"] == 1

    def test_get_current_user_expired_token(self):
        """测试过期JWT令牌"""
        payload = {
            "sub": "admin",
            "user_id": 1,
            "role": "user",
            "exp": datetime.utcnow() - timedelta(hours=1)
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(Exception) as exc_info:
            get_current_user(token)
        assert "expired" in str(exc_info.value).lower()

    def test_get_current_admin_required(self):
        """测试管理员权限"""
        # 普通用户
        user = {"username": "user", "role": "user"}
        with pytest.raises(Exception) as exc_info:
            get_current_admin(user)
        assert "admin privileges required" in str(exc_info.value).lower()

        # 管理员用户
        admin = {"username": "admin", "role": "admin"}
        result = get_current_admin(admin)
        assert result == admin


class TestMonitorAPI:
    """监控API测试"""

    @patch('user_interface.backend.routers.monitor.monitor_manager')
    def test_get_monitor_status(self, mock_monitor_manager):
        """测试获取监控状态接口"""
        mock_monitor_manager.get_status.return_value = {
            "overall_status": "healthy",
            "active_alerts": 0,
            "last_check_time": datetime.now().isoformat(),
            "monitors": [
                {"name": "data_quality", "status": "ok"},
                {"name": "collection", "status": "ok"}
            ]
        }

        headers = {"X-API-Key": settings.API_KEYS[0]}
        # 同时需要JWT认证
        payload = {
            "sub": "admin",
            "user_id": 1,
            "role": "admin",
            "exp": datetime.utcnow() + timedelta(hours=1)
        }
        token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        headers["Authorization"] = f"Bearer {token}"

        response = client.get("/api/v1/monitor/status", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert data["code"] == 0
        assert data["data"]["overall_status"] == "healthy"
        assert data["data"]["active_alerts"] == 0


class TestRateLimiting:
    """限流中间件测试"""

    def test_rate_limiting(self):
        """测试接口限流"""
        headers = {"X-API-Key": settings.API_KEYS[0]}

        # 快速发送多个请求
        responses = []
        for i in range(10):
            response = client.get("/api/v1/health", headers=headers)
            responses.append(response.status_code)

        # 应该有部分请求被限流
        assert 429 in responses


class TestWebSocketAPI:
    """WebSocket API测试"""

    @patch('user_interface.backend.websocket.query_manager')
    def test_websocket_subscription(self, mock_query_manager):
        """测试WebSocket订阅"""
        # 模拟实时数据推送
        mock_result = Mock()
        mock_result.success = True
        mock_result.data.to_dict.return_value = [{
            "stock_code": "000001.SZ",
            "price": 10.0,
            "time": datetime.now().isoformat()
        }]
        mock_query_manager.execute_query.return_value = mock_result

        with client.websocket_connect("/ws/market?api_key=" + settings.API_KEYS[0]) as websocket:
            # 发送订阅消息
            subscribe_msg = {
                "action": "subscribe",
                "stock_codes": ["000001.SZ", "600000.SH"]
            }
            websocket.send_text(json.dumps(subscribe_msg))

            # 接收订阅确认
            response = websocket.receive_json()
            assert response["type"] == "subscription_confirmation"
            assert response["subscribed_stocks"] == ["000001.SZ", "600000.SH"]

            # 接收行情数据
            data_msg = websocket.receive_json()
            assert data_msg["type"] == "market_data"
            assert "data" in data_msg
            assert any(d["stock_code"] == "000001.SZ" for d in data_msg["data"])
