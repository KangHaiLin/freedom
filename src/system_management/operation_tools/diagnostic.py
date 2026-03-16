"""
运维工具 - 系统诊断
收集系统信息、依赖版本、配置诊断、权限检查，生成诊断报告
"""
import os
import sys
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional
import importlib.metadata


class SystemDiagnostic:
    """
    系统诊断工具
    收集：
    - Python 版本、系统信息
    - 已安装依赖版本
    - 配置文件检查
    - 目录权限检查
    - 生成诊断报告
    """

    def collect_system_info(self) -> Dict[str, Any]:
        """收集系统信息"""
        return {
            'os': platform.system(),
            'os_release': platform.release(),
            'os_version': platform.version(),
            'architecture': platform.machine(),
            'python_version': platform.python_version(),
            'python_implementation': platform.python_implementation(),
            'hostname': platform.node(),
            'cwd': str(Path.cwd()),
            'pid': os.getpid(),
        }

    def collect_dependency_versions(self, packages: Optional[List[str]] = None) -> Dict[str, Optional[str]]:
        """
        收集依赖包版本

        Args:
            packages: 要收集的包名列表，None 收集主要量化相关包
        """
        if packages is None:
            packages = [
                'pandas', 'numpy', 'scipy', 'scikit-learn', 'ta-lib',
                'pytest', 'fastapi', 'sqlalchemy', 'psycopg2-binary',
                'clickhouse-driver', 'influxdb-client', 'redis',
                'psutil', 'pyyaml', 'croniter',
            ]

        versions: Dict[str, Optional[str]] = {}
        for pkg in packages:
            try:
                versions[pkg] = importlib.metadata.version(pkg)
            except importlib.metadata.PackageNotFoundError:
                try:
                    # 尝试导入获取版本
                    module = importlib.import_module(pkg.replace('-', '_'))
                    versions[pkg] = getattr(module, '__version__', 'unknown')
                except (ImportError, AttributeError):
                    versions[pkg] = None
            except Exception:
                versions[pkg] = 'error'

        return versions

    def check_config_directory(
        self,
        config_dir: str | Path = "config",
    ) -> Dict[str, Any]:
        """检查配置目录"""
        config_path = Path(config_dir)
        result: Dict[str, Any] = {
            'exists': config_path.exists(),
            'is_directory': False,
            'readable': False,
            'writable': False,
            'files': [],
            'issues': [],
        }

        if not result['exists']:
            result['issues'].append("配置目录不存在")
            return result

        result['is_directory'] = config_path.is_dir()
        if not result['is_directory']:
            result['issues'].append("配置路径不是目录")
            return result

        # 检查权限
        result['readable'] = os.access(config_path, os.R_OK)
        if not result['readable']:
            result['issues'].append("配置目录不可读")

        result['writable'] = os.access(config_path, os.W_OK)
        if not result['writable']:
            result['issues'].append("配置目录不可写")

        # 列出配置文件
        extensions = ['.yaml', '.yml', '.json', '.env', '.ini']
        for ext in extensions:
            for f in config_path.glob(f"**/*{ext}"):
                if f.is_file():
                    rel_path = str(f.relative_to(config_path))
                    result['files'].append({
                        'path': rel_path,
                        'size_bytes': f.stat().st_size,
                        'readable': os.access(f, os.R_OK),
                    })
                    if not os.access(f, os.R_OK):
                        result['issues'].append(f"配置文件 {rel_path} 不可读")

        return result

    def check_data_directory(
        self,
        data_dir: str | Path = "data",
    ) -> Dict[str, Any]:
        """检查数据目录"""
        data_path = Path(data_dir)
        result: Dict[str, Any] = {
            'exists': data_path.exists(),
            'is_directory': False,
            'readable': False,
            'writable': False,
            'total_size_bytes': 0,
            'file_count': 0,
            'issues': [],
        }

        if not result['exists']:
            result['issues'].append("数据目录不存在，建议创建")
            return result

        result['is_directory'] = data_path.is_dir()
        if not result['is_directory']:
            result['issues'].append("数据路径不是目录")
            return result

        result['readable'] = os.access(data_path, os.R_OK)
        if not result['readable']:
            result['issues'].append("数据目录不可读")

        result['writable'] = os.access(data_path, os.W_OK)
        if not result['writable']:
            result['issues'].append("数据目录不可写")

        # 统计文件和大小
        total_size = 0
        file_count = 0
        for f in data_path.glob("**/*"):
            if f.is_file():
                file_count += 1
                try:
                    total_size += f.stat().st_size
                except Exception:
                    pass

        result['total_size_bytes'] = total_size
        result['file_count'] = file_count

        if file_count == 0:
            result['issues'].append("数据目录为空")

        return result

    def check_log_directory(
        self,
        log_dir: str | Path = "logs",
    ) -> Dict[str, Any]:
        """检查日志目录"""
        log_path = Path(log_dir)
        result: Dict[str, Any] = {
            'exists': log_path.exists(),
            'is_directory': False,
            'readable': False,
            'writable': False,
            'issues': [],
        }

        if not result['exists']:
            try:
                log_path.mkdir(parents=True, exist_ok=True)
                result['created'] = True
                result['exists'] = True
            except Exception as e:
                result['created'] = False
                result['issues'].append(f"创建日志目录失败: {str(e)}")
                return result

        result['is_directory'] = log_path.is_dir()
        result['readable'] = os.access(log_path, os.R_OK)
        result['writable'] = os.access(log_path, os.W_OK)

        if not result['readable']:
            result['issues'].append("日志目录不可读")
        if not result['writable']:
            result['issues'].append("日志目录不可写")

        return result

    def check_python_path(self) -> Dict[str, Any]:
        """检查 Python 路径"""
        return {
            'sys_path': [str(p) for p in sys.path],
            'virtual_env': os.environ.get('VIRTUAL_ENV', None),
            'is_virtual_env': hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
        }

    def generate_report(
        self,
        include_packages: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """生成完整诊断报告"""
        report = {
            'timestamp': os.times()[4],
            'system_info': self.collect_system_info(),
            'dependencies': self.collect_dependency_versions(include_packages),
            'config_directory': self.check_config_directory(),
            'data_directory': self.check_data_directory(),
            'log_directory': self.check_log_directory(),
            'python_path': self.check_python_path(),
        }

        # 收集所有问题
        all_issues: List[str] = []
        for section in ['config_directory', 'data_directory', 'log_directory']:
            if 'issues' in report[section]:
                all_issues.extend(report[section]['issues'])

        report['all_issues'] = all_issues
        report['issue_count'] = len(all_issues)

        return report

    def export_report_markdown(
        self,
        output_path: Optional[str | Path] = None,
    ) -> str:
        """导出诊断报告为 Markdown 格式"""
        report = self.generate_report()
        lines: List[str] = []

        lines.append("# 系统诊断报告\n")
        lines.append(f"生成时间: `{report['timestamp']:.0f}`\n")

        lines.append("## 系统信息\n")
        sys_info = report['system_info']
        for key, value in sys_info.items():
            lines.append(f"- **{key}**: `{value}`")
        lines.append("")

        lines.append("## 依赖版本\n")
        deps = report['dependencies']
        lines.append("| Package | Version | Status |")
        lines.append("|---------|---------|--------|")
        for pkg, version in sorted(deps.items()):
            if version is None:
                lines.append(f"| {pkg} | **not installed** | ⚠️ |")
            else:
                lines.append(f"| {pkg} | {version} | ✅ |")
        lines.append("")

        lines.append("## 目录检查\n")

        for name, title in [
            ('config_directory', '配置目录'),
            ('data_directory', '数据目录'),
            ('log_directory', '日志目录'),
        ]:
            section = report[name]
            lines.append(f"### {title}\n")
            lines.append(f"- 存在: {'✅ 是' if section['exists'] else '❌ 否'}")
            if section['exists']:
                lines.append(f"- 是目录: {'✅ 是' if section['is_directory'] else '❌ 否'}")
                lines.append(f"- 可读: {'✅ 是' if section['readable'] else '❌ 否'}")
                lines.append(f"- 可写: {'✅ 是' if section['writable'] else '❌ 否'}")
            if 'issues' in section and section['issues']:
                lines.append("\n问题:")
                for issue in section['issues']:
                    lines.append(f"- ⚠️ {issue}")
            lines.append("")

        if report['all_issues']:
            lines.append("## 所有问题\n")
            for issue in report['all_issues']:
                lines.append(f"- ⚠️ {issue}")
            lines.append("")
        else:
            lines.append("## 结论\n")
            lines.append("✅ 未发现问题，系统诊断通过。\n")

        markdown = "\n".join(lines)

        if output_path is not None:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(markdown)

        return markdown
