"""
策略加载器
动态加载策略类
"""

import importlib
import sys
from pathlib import Path
from typing import Optional, Type

from src.strategy_research.base import BaseStrategy


class StrategyLoader:
    """策略加载器"""

    def __init__(self, strategy_dir: str = "strategies"):
        self._strategy_dir = Path(strategy_dir)
        if str(self._strategy_dir) not in sys.path:
            sys.path.insert(0, str(self._strategy_dir))

    def load_class(self, class_path: str) -> Optional[Type[BaseStrategy]]:
        """
        从类路径加载策略类

        Args:
            class_path: 类路径 e.g. "momentum.MomentumStrategy"

        Returns:
            策略类，加载失败返回None
        """
        try:
            if "." in class_path:
                module_name, class_name = class_path.rsplit(".", 1)
            else:
                module_name = class_path
                class_name = class_path

            module = importlib.import_module(module_name)
            strategy_class = getattr(module, class_name)

            if not issubclass(strategy_class, BaseStrategy):
                return None

            return strategy_class
        except Exception as e:
            import logging

            logging.error(f"Failed to load strategy {class_path}: {e}")
            return None

    def reload_class(self, class_path: str) -> Optional[Type[BaseStrategy]]:
        """重新加载策略类"""
        if "." in class_path:
            module_name, _ = class_path.rsplit(".", 1)
        else:
            module_name = class_path

        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])

        return self.load_class(class_path)

    def create_instance(
        self,
        class_path: str,
        params: Optional[dict] = None,
    ) -> Optional[BaseStrategy]:
        """创建策略实例"""
        strategy_class = self.load_class(class_path)
        if strategy_class is None:
            return None
        return strategy_class(params=params or {})
