"""
系统管理子系统
负责统一配置管理、日志管理、监控、运维工具、任务调度

提供完整的后端基础设施支撑，是整个系统的基础设施层。

导出:
- system_manager: 全局系统管理器单例
- get_system_manager: 获取系统管理器实例
- 各子模块公共接口
"""
from .configuration_center import (
    ConfigSource,
    ConfigProvider,
    FileConfigSource,
    EnvConfigSource,
    ConfigManager,
    get_config_manager,
)
from .log_center import (
    BaseLogger,
    LogLevel,
    LogRecord,
    ConsoleLogger,
    FileLogger,
    StructuredLogger,
    LogManager,
    ModuleLogger,
    get_log_manager,
    get_logger,
)
from .monitoring_center import (
    BaseMonitor,
    SystemMonitor,
    ApplicationMonitor,
    MetricsCollector,
    MonitorManager,
    get_monitor_manager,
)
from .operation_tools import (
    HealthCheckResult,
    HealthChecker,
    HealthCheckManager,
    SystemDiagnostic,
    Maintenance,
)
from .task_scheduler import (
    BaseTask,
    TaskStatus,
    TaskResult,
    ScheduledTask,
    AsyncTask,
    AsyncTaskQueue,
    TaskRegistry,
    SchedulerManager,
    get_scheduler_manager,
)
from .system_manager import SystemManager, system_manager, get_system_manager

__all__ = [
    # 配置中心
    'ConfigSource',
    'ConfigProvider',
    'FileConfigSource',
    'EnvConfigSource',
    'ConfigManager',
    'get_config_manager',
    # 日志中心
    'BaseLogger',
    'LogLevel',
    'LogRecord',
    'ConsoleLogger',
    'FileLogger',
    'StructuredLogger',
    'LogManager',
    'ModuleLogger',
    'get_log_manager',
    'get_logger',
    # 监控中心
    'BaseMonitor',
    'SystemMonitor',
    'ApplicationMonitor',
    'MetricsCollector',
    'MonitorManager',
    'get_monitor_manager',
    # 运维工具
    'HealthCheckResult',
    'HealthChecker',
    'HealthCheckManager',
    'SystemDiagnostic',
    'Maintenance',
    # 任务调度
    'BaseTask',
    'TaskStatus',
    'TaskResult',
    'ScheduledTask',
    'AsyncTask',
    'AsyncTaskQueue',
    'TaskRegistry',
    'SchedulerManager',
    'get_scheduler_manager',
    # 统一入口
    'SystemManager',
    'system_manager',
    'get_system_manager',
]

__version__ = "1.0.0"
