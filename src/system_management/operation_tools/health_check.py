"""
运维工具 - 系统健康检查
检查各子系统连接、存储、配置等健康状态
"""

import os
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class HealthCheckResult:
    """健康检查结果"""

    def __init__(
        self,
        check_name: str,
        healthy: bool,
        message: str = "",
        details: Optional[Dict[str, Any]] = None,
    ):
        self.check_name = check_name
        self.healthy = healthy
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "check_name": self.check_name,
            "healthy": self.healthy,
            "message": self.message,
            "details": self.details,
        }


class HealthChecker:
    """
    系统健康检查器
    支持：
    - 磁盘空间检查
    - 内存使用检查
    - 目录权限检查
    - 配置文件检查
    - 自定义检查扩展
    """

    def __init__(self):
        """初始化"""
        self._checks: List[Tuple[str, callable]] = []
        self._register_default_checks()

    def _register_default_checks(self) -> None:
        """注册默认检查"""
        pass

    def add_check(self, name: str, check_func) -> None:
        """
        添加自定义检查

        Args:
            name: 检查名称
            check_func: 检查函数，返回 HealthCheckResult
        """
        self._checks.append((name, check_func))

    def check_disk_space(
        self,
        path: str | Path,
        min_free_percent: float = 10.0,
        min_free_gb: float = 5.0,
    ) -> HealthCheckResult:
        """
        检查路径所在磁盘空间

        Args:
            path: 检查路径
            min_free_percent: 最小可用百分比
            min_free_gb: 最小可用 GB
        """
        path = Path(path)
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

            stat = os.statvfs(path)
            free_bytes = stat.f_frsize * stat.f_bfree
            total_bytes = stat.f_frsize * stat.f_blocks
            free_gb = free_bytes / (1024**3)
            free_percent = (free_bytes / total_bytes) * 100

            details = {
                "total_gb": total_bytes / (1024**3),
                "free_gb": free_gb,
                "free_percent": free_percent,
            }

            if free_gb < min_free_gb or free_percent < min_free_percent:
                return HealthCheckResult(
                    check_name="disk_space",
                    healthy=False,
                    message=f"磁盘空间不足: {free_gb:.1f} GB ({free_percent:.1f}%)，需要至少 {min_free_gb} GB ({min_free_percent}%)",
                    details=details,
                )

            return HealthCheckResult(
                check_name="disk_space",
                healthy=True,
                message=f"磁盘空间正常: {free_gb:.1f} GB ({free_percent:.1f}%)",
                details=details,
            )

        except Exception as e:
            return HealthCheckResult(
                check_name="disk_space",
                healthy=False,
                message=f"检查磁盘空间失败: {str(e)}",
                details={"error": str(e)},
            )

    def check_memory(
        self,
        min_free_percent: float = 10.0,
        min_free_gb: float = 1.0,
    ) -> HealthCheckResult:
        """检查可用内存"""
        import psutil

        try:
            mem = psutil.virtual_memory()
            free_gb = mem.available / (1024**3)
            free_percent = mem.available / mem.total * 100

            details = {
                "total_gb": mem.total / (1024**3),
                "available_gb": free_gb,
                "available_percent": free_percent,
                "used_percent": mem.percent,
            }

            if free_gb < min_free_gb or free_percent < min_free_percent:
                return HealthCheckResult(
                    check_name="memory",
                    healthy=False,
                    message=f"内存不足: {free_gb:.1f} GB ({free_percent:.1f}%)，需要至少 {min_free_gb} GB ({min_free_percent}%)",
                    details=details,
                )

            return HealthCheckResult(
                check_name="memory",
                healthy=True,
                message=f"内存正常: {free_gb:.1f} GB ({free_percent:.1f}%)",
                details=details,
            )

        except Exception as e:
            return HealthCheckResult(
                check_name="memory",
                healthy=False,
                message=f"检查内存失败: {str(e)}",
                details={"error": str(e)},
            )

    def check_directory_writable(self, path: str | Path) -> HealthCheckResult:
        """检查目录是否可写"""
        path = Path(path)
        check_name = f"directory_writable_{path}"
        try:
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

            # 尝试写一个测试文件
            test_file = path / f".health_check_test_{os.getpid()}"
            with open(test_file, "w") as f:
                f.write("test")
            test_file.unlink()

            return HealthCheckResult(
                check_name=check_name,
                healthy=True,
                message=f"目录 {path} 可写",
            )

        except Exception as e:
            return HealthCheckResult(
                check_name=check_name,
                healthy=False,
                message=f"目录 {path} 不可写: {str(e)}",
                details={"error": str(e), "path": str(path)},
            )

    def check_config_file(self, path: str | Path) -> HealthCheckResult:
        """检查配置文件是否存在且可读"""
        path = Path(path)
        check_name = f"config_file_{path.name}"
        try:
            if not path.exists():
                return HealthCheckResult(
                    check_name=check_name,
                    healthy=False,
                    message=f"配置文件 {path} 不存在",
                )

            if not path.is_file():
                return HealthCheckResult(
                    check_name=check_name,
                    healthy=False,
                    message=f"{path} 不是文件",
                )

            # 尝试读取
            with open(path, "r") as f:
                f.read(100)

            return HealthCheckResult(
                check_name=check_name,
                healthy=True,
                message=f"配置文件 {path} 可读",
                details={"size_bytes": path.stat().st_size},
            )

        except Exception as e:
            return HealthCheckResult(
                check_name=check_name,
                healthy=False,
                message=f"读取配置文件 {path} 失败: {str(e)}",
                details={"error": str(e)},
            )

    def check_tcp_port(self, host: str, port: int) -> HealthCheckResult:
        """检查 TCP 端口是否可连接"""
        check_name = f"tcp_port_{host}:{port}"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                return HealthCheckResult(
                    check_name=check_name,
                    healthy=True,
                    message=f"端口 {host}:{port} 可连接",
                )
            else:
                return HealthCheckResult(
                    check_name=check_name,
                    healthy=False,
                    message=f"端口 {host}:{port} 不可连接",
                )

        except Exception as e:
            return HealthCheckResult(
                check_name=check_name,
                healthy=False,
                message=f"检查端口 {host}:{port} 失败: {str(e)}",
                details={"error": str(e)},
            )

    def check_database_connection(self, name: str, connector) -> HealthCheckResult:
        """检查数据库连接"""
        check_name = f"database_connection_{name}"
        try:
            is_connected = connector()
            if is_connected:
                return HealthCheckResult(
                    check_name=check_name,
                    healthy=True,
                    message=f"{name} 数据库连接正常",
                )
            else:
                return HealthCheckResult(
                    check_name=check_name,
                    healthy=False,
                    message=f"{name} 数据库连接失败",
                )

        except Exception as e:
            return HealthCheckResult(
                check_name=check_name,
                healthy=False,
                message=f"{name} 数据库连接异常: {str(e)}",
                details={"error": str(e)},
            )

    def run_all(self) -> Dict[str, Any]:
        """
        运行所有健康检查

        Returns:
            汇总结果：总体健康状态、所有检查详情
        """
        results: List[HealthCheckResult] = []

        # 运行预定义的默认检查
        # 检查当前目录磁盘空间
        results.append(self.check_disk_space(Path.cwd()))
        # 检查内存
        results.append(self.check_memory())

        # 运行用户添加的自定义检查
        for name, check_func in self._checks:
            try:
                result = check_func()
                results.append(result)
            except Exception as e:
                results.append(
                    HealthCheckResult(
                        check_name=name,
                        healthy=False,
                        message=f"检查抛出异常: {str(e)}",
                        details={"error": str(e)},
                    )
                )

        # 汇总
        all_healthy = all(r.healthy for r in results)
        unhealthy = [r for r in results if not r.healthy]

        return {
            "overall_healthy": all_healthy,
            "total_checks": len(results),
            "healthy_count": sum(1 for r in results if r.healthy),
            "unhealthy_count": len(unhealthy),
            "unhealthy_checks": [r.to_dict() for r in unhealthy],
            "all_results": [r.to_dict() for r in results],
        }


class HealthCheckManager:
    """健康检查管理器，统一入口"""

    def __init__(self):
        self._checker = HealthChecker()

    def add_check(self, name: str, check_func) -> None:
        """添加自定义检查"""
        self._checker.add_check(name, check_func)

    def check_all(self) -> Dict[str, Any]:
        """运行所有检查"""
        return self._checker.run_all()

    def is_healthy(self) -> bool:
        """检查整体是否健康"""
        result = self.check_all()
        return result["overall_healthy"]
