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


def test_activate_version():
    """Test activating a specific version"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="test",
            strategy_name="Test",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={"param": 1},
        )
        manager.create_new_version("test", "1.1.0", {"param": 2})

        # Activate version 1
        success = manager.activate_version("test", 1)
        assert success is True
        meta = manager.get_metadata("test")
        assert meta.current_version == 1
        assert any(v.version_id == 1 and v.is_active for v in meta.versions)
        assert any(v.version_id == 2 and not v.is_active for v in meta.versions)


def test_activate_version_not_found():
    """Test activate version when strategy doesn't exist returns False"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        success = manager.activate_version("nonexistent", 1)
        assert success is False


def test_update_status():
    """Test updating strategy status"""
    from src.strategy_research.base import StrategyStatus
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="test",
            strategy_name="Test",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={},
        )

        success = manager.update_status("test", StrategyStatus.READY)
        assert success is True
        meta = manager.get_metadata("test")
        assert meta.status == StrategyStatus.READY


def test_update_status_not_found():
    """Test update status when strategy doesn't exist returns False"""
    from src.strategy_research.base import StrategyStatus
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        success = manager.update_status("nonexistent", StrategyStatus.RUNNING)
        assert success is False


def test_delete_strategy():
    """Test deleting a strategy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="test",
            strategy_name="Test",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={},
        )

        assert manager.count() == 1
        success = manager.delete_strategy("test")
        assert success is True
        assert manager.count() == 0


def test_list_strategies_filter_by_status():
    """Test listing strategies filtered by status"""
    from src.strategy_research.base import StrategyStatus
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
        manager.update_status("t1", StrategyStatus.READY)

        result = manager.list_strategies(status=StrategyStatus.READY)
        assert len(result) == 1
        assert result[0].strategy_id == "t1"


def test_list_strategies_filter_by_tag():
    """Test listing strategies filtered by tag"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="t1",
            strategy_name="T1",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={},
            tags=["momentum", "trend"],
        )
        manager.create_strategy(
            strategy_id="t2",
            strategy_name="T2",
            strategy_class_path="b.B",
            description="",
            author="test",
            params={},
            tags=["mean-reversion"],
        )

        result = manager.list_strategies(tag="momentum")
        assert len(result) == 1
        assert result[0].strategy_id == "t1"


def test_get_metadata_not_found():
    """Test get_metadata returns None for non-existent strategy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        result = manager.get_metadata("nonexistent")
        assert result is None


def test_instantiate_not_found():
    """Test instantiate returns None for non-existent strategy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        result = manager.instantiate("nonexistent")
        assert result is None


def test_instantiate_no_active_version():
    """Test instantiate returns None when no active version"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="test",
            strategy_name="Test",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={"param": 1},
        )
        # Deactivate all versions
        meta = manager.get_metadata("test")
        for v in meta.versions:
            v.is_active = False
        manager._storage.update_strategy(meta)

        result = manager.instantiate("test")
        assert result is None


def test_instantiate_with_version():
    """Test instantiating with specific version"""
    import tempfile
    import os
    from src.strategy_research.base import BaseStrategy

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a simple strategy module for testing
        strategies_dir = os.path.join(tmpdir, "strategies")
        os.makedirs(strategies_dir)
        with open(os.path.join(strategies_dir, "test_strategy.py"), "w") as f:
            f.write('''
from src.strategy_research.base import BaseStrategy
class TestStrategy(BaseStrategy):
    def on_bar(self, bar_data, current_date, portfolio):
        return {}
''')

        manager = StrategyManager(
            storage_dir=f"{tmpdir}/meta",
            strategy_dir=strategies_dir,
        )
        manager.create_strategy(
            strategy_id="test",
            strategy_name="Test",
            strategy_class_path="test_strategy.TestStrategy",
            description="",
            author="test",
            params={"param": 1},
        )

        instance = manager.instantiate_with_version("test", 1)
        assert instance is not None
        assert isinstance(instance, BaseStrategy)
        assert instance.strategy_name == "Test"
        assert instance.params == {"param": 1}


def test_instantiate_with_version_not_found():
    """Test instantiate with version when version doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="test",
            strategy_name="Test",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={},
        )

        result = manager.instantiate_with_version("test", 99)
        assert result is None


def test_health_check():
    """Test health_check returns correct info"""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = StrategyManager(storage_dir=f"{tmpdir}/strategies")
        manager.create_strategy(
            strategy_id="test",
            strategy_name="Test",
            strategy_class_path="a.A",
            description="",
            author="test",
            params={},
        )

        health = manager.health_check()
        assert health["status"] == "ok"
        assert health["total_strategies"] == 1
        assert "storage_dir" in health
