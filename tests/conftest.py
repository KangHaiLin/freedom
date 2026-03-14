"""
pytest配置文件
"""
import pytest
import sys
import os
from pathlib import Path

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 测试配置
os.environ["ENV"] = "test"
os.environ["DEBUG"] = "True"
os.environ["API_KEY_ENABLED"] = "False"
os.environ["RATE_LIMIT"] = "0"  # 关闭限流
