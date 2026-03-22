"""
Unit tests for strategy management
"""

import tempfile

from src.strategy_research.strategy_management import StrategyManager, StrategyMetadata, StrategyVersion


def test_create_strategy():
    """Test creating strategy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        success, msg, meta = manager.create_strategy(
            strategy_id="test-momentum",
            strategy_name="Momentum Strategy",
            strategy_class_path="strategies.momentum.MomentumStrategy",
            description="Simple momentum strategy",
            author="test",
            params={"lookback": 20, "top_n": 10},
            tags=["momentum", "trend"],
        )

        assert success is True
        assert meta is not None
        assert meta.strategy_id == "test-momentum"
        assert len(meta.versions) == 1
        assert meta.current_active_version is not None
        assert meta.current_active_version.version_id == 1


def test_add_version():
    """Test adding new version"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="test-momentum",
            strategy_name="Momentum Strategy",
            strategy_class_path="strategies.momentum.MomentumStrategy",
            description="Simple momentum strategy",
            author="test",
            params={"lookback": 20, "top_n": 10},
        )

        success, msg, version = manager.create_new_version(
            "test-momentum",
            "1.1.0",
            {"lookback": 30, "top_n": 10},
            change_note="Adjust lookback period",
        )

        assert success is True
        meta = manager.get_metadata("test-momentum")
        assert len(meta.versions) == 2
        # new version is active
        assert any(v.version_id == 2 and v.is_active for v in meta.versions)


def test_list_strategies():
    """Test listing strategies"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="t1",
            strategy_name="T1",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={},
        )
        manager.create_strategy(
            strategy_id="t2",
            strategy_name="T2",
            strategy_class_path="b.B",
            description="",
            author="test",
            params={},
        )

        strategies = manager.list_strategies()
        assert len(strategies) == 2


def test_count():
    """Test count"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="t1",
            strategy_name="T1",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={},
        )
        assert manager.count() == 1
