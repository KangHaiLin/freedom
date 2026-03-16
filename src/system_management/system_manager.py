"""
系统管理统一入口 - SystemManager
整合所有子模块，提供统一接口，全局单例
遵循项目 *Manager 模式
"""
import threading
from typing import Any, Callable, Dict, Optional, Type, TypeVar
from pathlib import Path

from .configuration_center import ConfigManager, get_config_manager
from .log_center import LogManager, get_log_manager, ModuleLogger, get_logger
from .monitoring_center import MonitorManager, get_monitor_manager
from .operation_tools import HealthCheckManager, SystemDiagnostic, Maintenance
from .task_scheduler import SchedulerManager, get_scheduler_manager

T = TypeVar('T')


class SystemManager:
    """
    系统管理器
    整合所有系统管理子模块，提供统一入口
    全局单例模式
    """

    _instance: Optional['SystemManager'] = None
    _lock: threading.Lock = threading.Lock()

    def __new__(cls) -> 'SystemManager':
        """单例创建"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化，只执行一次"""
        if getattr(self, '_initialized', False):
            return
        self._initialized = True

        # 子模块管理器实例
        self._config_manager: Optional[ConfigManager] = None
        self._log_manager: Optional[LogManager] = None
        self._monitor_manager: Optional[MonitorManager] = None
        self._scheduler_manager: Optional[SchedulerManager] = None

        # 运维工具
        self._health_check: Optional[HealthCheckManager] = None
        self._diagnostic: Optional[SystemDiagnostic] = None
        self._maintenance: Optional[Maintenance] = None

        # 是否启动
        self._started = False

    def initialize(
        self,
        config_file: Optional[str | Path] = None,
        enable_hotreload: bool = True,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        structured_log_file: Optional[str] = None,
        enable_structured_logging: bool = True,
        log_retention_days: int = 30,
        monitor_interval_seconds: float = 15.0,
        max_concurrent_async_tasks: int = 10,
        auto_start: bool = True,
    ) -> None:
        """
        初始化所有系统管理模块

        Args:
            config_file: 配置文件路径
            enable_hotreload: 是否启用配置热重载
            log_level: 日志级别
            log_file: 文件日志路径
            structured_log_file: 结构化日志路径
            enable_structured_logging: 是否启用结构化日志
            log_retention_days: 日志保留天数
            monitor_interval_seconds: 监控采集间隔
            max_concurrent_async_tasks: 最大并发异步任务
            auto_start: 是否自动启动所有服务
        """
        # 初始化配置中心
        self._config_manager = get_config_manager()
        if config_file is not None:
            self._config_manager.initialize(
                config_file=config_file,
                enable_hotreload=enable_hotreload,
            )
        else:
            # 只初始化环境变量配置
            self._config_manager.initialize()

        # 初始化日志中心
        self._log_manager = get_log_manager()
        self._log_manager.initialize(
            level=log_level,
            log_file=log_file,
            structured_log_file=structured_log_file,
            enable_structured=enable_structured_logging,
            retention_days=log_retention_days,
        )

        # 初始化监控中心
        self._monitor_manager = get_monitor_manager()
        self._monitor_manager.initialize(
            collect_interval_seconds=monitor_interval_seconds,
            auto_start=False,
        )

        # 初始化任务调度
        self._scheduler_manager = get_scheduler_manager()
        self._scheduler_manager.initialize(
            max_concurrent_async=max_concurrent_async_tasks,
            auto_start=False,
        )

        # 初始化运维工具
        self._health_check = HealthCheckManager()
        self._diagnostic = SystemDiagnostic()
        self._maintenance = Maintenance()

        # 自动启动
        if auto_start:
            self.start()

    def start(self) -> None:
        """启动所有后台服务"""
        if self._started:
            return

        # 启动监控采集
        if self._monitor_manager:
            self._monitor_manager.start()

        # 启动任务调度
        if self._scheduler_manager:
            self._scheduler_manager.start()

        self._started = True
        self.get_logger("system_manager").info("SystemManager started")

    def stop(self) -> None:
        """停止所有后台服务"""
        if not self._started:
            return

        # 停止任务调度
        if self._scheduler_manager:
            self._scheduler_manager.shutdown()

        # 停止监控
        if self._monitor_manager:
            self._monitor_manager.shutdown()

        # 停止配置热重载
        if self._config_manager:
            self._config_manager.shutdown()

        self._started = False
        if self._log_manager:
            self._log_manager.info("SystemManager stopped", "system_manager")

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._started

    # ========== 配置快捷方法 ==========

    @property
    def config(self) -> ConfigManager:
        """获取配置管理器"""
        if self._config_manager is None:
            raise RuntimeError("SystemManager not initialized")
        return self._config_manager

    def get_config(
        self,
        key: str,
        default: Any = None,
        expected_type: Optional[Type[T]] = None,
    ) -> Optional[T]:
        """获取配置快捷方法"""
        return self.config.get(key, default, expected_type)

    def get_config_required(
        self,
        key: str,
        expected_type: Optional[Type[T]] = None,
    ) -> T:
        """获取必须配置"""
        return self.config.get_required(key, expected_type)

    # ========== 日志快捷方法 ==========

    @property
    def log(self) -> LogManager:
        """获取日志管理器"""
        if self._log_manager is None:
            raise RuntimeError("SystemManager not initialized")
        return self._log_manager

    def get_logger(self, module: str = "") -> ModuleLogger:
        """获取模块日志器"""
        return self.log.get_logger(module)

    def set_trace_id(self, trace_id: Optional[str]) -> None:
        """设置 trace_id"""
        self.log.set_trace_id(trace_id)

    # ========== 监控快捷方法 ==========

    @property
    def monitor(self) -> MonitorManager:
        """获取监控管理器"""
        if self._monitor_manager is None:
            raise RuntimeError("SystemManager not initialized")
        return self._monitor_manager

    def get_metrics(self) -> Dict[str, Any]:
        """获取指标快照"""
        return self.monitor.get_metrics_snapshot()

    def record_request(
        self,
        latency_seconds: float,
        is_error: bool = False,
    ) -> None:
        """记录请求"""
        self.monitor.record_request(latency_seconds, is_error)

    def check_health(self) -> Dict[str, Any]:
        """统一健康检查"""
        result = self.monitor.check_health()

        # 添加健康检查管理器的结果
        if self._health_check:
            custom_checks = self._health_check.check_all()
            result['custom_checks'] = custom_checks
            result['overall_healthy'] = (
                result['status'] in ('ok', 'warning') and
                custom_checks['overall_healthy']
            )

        return result

    # ========== 任务调度快捷方法 ==========

    @property
    def scheduler(self) -> SchedulerManager:
        """获取调度管理器"""
        if self._scheduler_manager is None:
            raise RuntimeError("SystemManager not initialized")
        return self._scheduler_manager

    def schedule_cron(
        self,
        cron_expr: str,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
    ) -> str:
        """添加 Cron 定时任务"""
        return self.scheduler.add_cron(cron_expr, callback, task_name)

    def schedule_interval(
        self,
        interval_seconds: float,
        callback: Callable[[], Any],
        task_name: Optional[str] = None,
        start_immediately: bool = True,
    ) -> str:
        """添加固定间隔定时任务"""
        return self.scheduler.add_interval(
            interval_seconds, callback, task_name, start_immediately
        )

    def submit_async(
        self,
        func: Callable[[], Any],
        priority: int = 0,
        on_complete: Optional[Callable[[Any], None]] = None,
        task_name: Optional[str] = None,
    ) -> str:
        """提交异步任务"""
        return self.scheduler.submit_async(
            func, priority, on_complete, task_name
        )

    # ========== 运维工具访问 ==========

    @property
    def health_check(self) -> HealthCheckManager:
        """获取健康检查管理器"""
        if self._health_check is None:
            raise RuntimeError("SystemManager not initialized")
        return self._health_check

    @property
    def diagnostic(self) -> SystemDiagnostic:
        """获取系统诊断工具"""
        if self._diagnostic is None:
            raise RuntimeError("SystemManager not initialized")
        return self._diagnostic

    @property
    def maintenance(self) -> Maintenance:
        """获取维护工具"""
        if self._maintenance is None:
            raise RuntimeError("SystemManager not initialized")
        return self._maintenance

    # ========== 完整诊断报告 ==========

    def generate_diagnostic_report(self, output_path: Optional[str | Path] = None) -> str:
        """生成完整诊断报告"""
        if output_path is not None:
            return self.diagnostic.export_report_markdown(output_path)
        report = self.diagnostic.generate_report()
        # 添加系统状态信息
        report['system_manager_running'] = self.is_running
        report['scheduler_stats'] = self.scheduler.get_stats()
        report['metrics'] = self.get_metrics()
        return str(report)

    def shutdown(self) -> None:
        """优雅关闭所有服务"""
        self.stop()


# 全局单例实例
system_manager = SystemManager()


def get_system_manager() -> SystemManager:
    """获取全局系统管理器实例"""
    return SystemManager()
