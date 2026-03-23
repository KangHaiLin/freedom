"""
Unit tests for strategy_loader.py
"""

import os
import sys
import tempfile
from pathlib import Path

from src.strategy_research.base import BaseStrategy
from src.strategy_research.strategy_management.strategy_loader import StrategyLoader


def create_test_strategy_file(tmp_dir):
    """Create a test strategy file on disk"""
    strategy_dir = Path(tmp_dir)
    strategy_file = strategy_dir / "test_strategy.py"
    content = """
from src.strategy_research.base import BaseStrategy

class TestStrategy(BaseStrategy):
    def on_bar(self, bar_data, current_date, portfolio):
        return {}

class NotAStrategy:
    pass
"""
    with open(strategy_file, "w") as f:
        f.write(content)
    return strategy_dir


def test_init():
    """Test initialization"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = StrategyLoader(tmpdir)
        assert loader._strategy_dir == Path(tmpdir)
        assert str(tmpdir) in sys.path


def test_load_class_success():
    """Test loading a valid strategy class"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_strategy_file(tmpdir)
        loader = StrategyLoader(tmpdir)

        strategy_class = loader.load_class("test_strategy.TestStrategy")
        assert strategy_class is not None
        assert issubclass(strategy_class, BaseStrategy)


def test_load_class_no_dot():
    """Test loading when class path has no dot"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_strategy_file(tmpdir)
        loader = StrategyLoader(tmpdir)

        # When module name == class name
        with open(Path(tmpdir) / "TestStrategy.py", "w") as f:
            f.write(
                """
from src.strategy_research.base import BaseStrategy\nclass TestStrategy(BaseStrategy):\n    def on_bar(self, bar_data, current_date, portfolio):\n        return {}\n"""
            )

        strategy_class = loader.load_class("TestStrategy")
        assert strategy_class is not None
        assert issubclass(strategy_class, BaseStrategy)


def test_load_class_not_subclass():
    """Test loading when class is not subclass of BaseStrategy returns None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_strategy_file(tmpdir)
        loader = StrategyLoader(tmpdir)

        strategy_class = loader.load_class("test_strategy.NotAStrategy")
        assert strategy_class is None


def test_load_class_module_not_found():
    """Test loading non-existent module returns None"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = StrategyLoader(tmpdir)

        strategy_class = loader.load_class("nonexistent_module.NonexistentClass")
        assert strategy_class is None


def test_reload_class():
    """Test reloading a strategy class"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_strategy_file(tmpdir)
        loader = StrategyLoader(tmpdir)

        # First load
        cls1 = loader.load_class("test_strategy.TestStrategy")
        assert cls1 is not None

        # Reload
        cls2 = loader.reload_class("test_strategy.TestStrategy")
        assert cls2 is not None
        assert cls1 is not cls2  # Different instance after reload


def test_create_instance_success():
    """Test creating a strategy instance"""
    with tempfile.TemporaryDirectory() as tmpdir:
        create_test_strategy_file(tmpdir)
        loader = StrategyLoader(tmpdir)

        instance = loader.create_instance("test_strategy.TestStrategy", {"param": 10})
        assert instance is not None
        assert isinstance(instance, BaseStrategy)


def test_create_instance_load_fail_returns_none():
    """Test create_instance returns None when loading fails"""
    with tempfile.TemporaryDirectory() as tmpdir:
        loader = StrategyLoader(tmpdir)
        instance = loader.create_instance("nonexistent.Module", {})
        assert instance is None
