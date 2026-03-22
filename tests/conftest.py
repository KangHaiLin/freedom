"""
pytest配置文件
"""

import os
import sys
from pathlib import Path

import pytest

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 测试配置
os.environ["ENV"] = "test"
os.environ["DEBUG"] = "True"
os.environ["API_KEY_ENABLED"] = "False"
os.environ["RATE_LIMIT"] = "0"  # 关闭限流

from datetime import datetime
from unittest.mock import Mock, patch

import pandas as pd
from fastapi.testclient import TestClient

# 不直接导入需要初始化的类，避免依赖配置
# from data_management.data_storage.storage_manager import StorageManager
# from data_management.data_ingestion.data_source_manager import DataSourceManager
# from data_management.data_query.query_manager import QueryManager
# from data_management.data_monitoring.monitor_manager import MonitorManager
# from user_interface.backend.main import app


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    return {
        "test_mode": True,
        "database": {"host": "localhost", "port": 5432, "database": "test_stock", "user": "test", "password": "test"},
        "redis": {"host": "localhost", "port": 6379, "db": 1},
    }


@pytest.fixture(scope="function")
def mock_storage_manager():
    """模拟存储管理器"""
    with patch("data_management.data_storage.storage_manager.StorageManager") as mock_class:
        mock_instance = Mock(spec=StorageManager)
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_data_source_manager():
    """模拟数据源管理器"""
    with patch("data_management.data_ingestion.data_source_manager.DataSourceManager") as mock_class:
        mock_instance = Mock(spec=DataSourceManager)
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_query_manager():
    """模拟查询管理器"""
    with patch("data_management.data_query.query_manager.QueryManager") as mock_class:
        mock_instance = Mock(spec=QueryManager)
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="function")
def mock_monitor_manager():
    """模拟监控管理器"""
    with patch("data_management.data_monitoring.monitor_manager.MonitorManager") as mock_class:
        mock_instance = Mock(spec=MonitorManager)
        mock_class.return_value = mock_instance
        yield mock_instance


@pytest.fixture(scope="module")
def test_client():
    """FastAPI测试客户端"""
    return TestClient(app)


@pytest.fixture
def sample_realtime_data():
    """实时行情测试数据"""
    return pd.DataFrame(
        {
            "stock_code": ["000001.SZ", "600000.SH", "000002.SZ", "600001.SH"],
            "price": [10.0, 15.0, 20.0, 25.0],
            "volume": [1000, 2000, 3000, 4000],
            "amount": [10000.0, 30000.0, 60000.0, 100000.0],
            "time": [datetime.now()] * 4,
        }
    )


@pytest.fixture
def sample_daily_data():
    """日线行情测试数据"""
    dates = pd.date_range(start="2023-01-01", end="2023-01-10")
    return pd.DataFrame(
        {
            "trade_date": dates,
            "stock_code": ["000001.SZ"] * 10,
            "open": [10.0 + i * 0.1 for i in range(10)],
            "high": [10.2 + i * 0.1 for i in range(10)],
            "low": [9.8 + i * 0.1 for i in range(10)],
            "close": [10.1 + i * 0.1 for i in range(10)],
            "volume": [100000 + i * 10000 for i in range(10)],
        }
    )
