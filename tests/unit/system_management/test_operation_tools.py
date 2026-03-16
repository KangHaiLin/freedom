"""
测试运维工具
"""
import tempfile
import os
from pathlib import Path
from src.system_management.operation_tools import (
    HealthChecker,
    SystemDiagnostic,
    Maintenance,
)


def test_health_check_disk_space():
    """测试磁盘空间检查"""
    checker = HealthChecker()
    result = checker.check_disk_space(Path.cwd(), min_free_gb=1)
    assert result.healthy
    assert result.details['free_gb'] > 0
    assert 'free_percent' in result.details


def test_health_check_memory():
    """测试内存检查"""
    checker = HealthChecker()
    result = checker.check_memory(min_free_gb=0.1)
    assert result.healthy
    assert 'available_gb' in result.details


def test_health_check_directory_writable(tmp_path):
    """测试目录可写检查"""
    checker = HealthChecker()
    result = checker.check_directory_writable(tmp_path)
    assert result.healthy

    # 创建一个只读目录测试
    if os.name != 'nt':  # 跳过 Windows
        readonly_dir = tmp_path / 'readonly'
        readonly_dir.mkdir()
        readonly_dir.chmod(0o555)
        result = checker.check_directory_writable(readonly_dir)
        assert not result.healthy


def test_health_check_run_all():
    """测试运行所有检查"""
    checker = HealthChecker()
    result = checker.run_all()
    assert 'overall_healthy' in result
    assert 'total_checks' in result
    assert result['total_checks'] >= 2
    assert 'unhealthy_checks' in result


def test_system_diagnostic_collect_system_info():
    """测试收集系统信息"""
    diagnostic = SystemDiagnostic()
    info = diagnostic.collect_system_info()

    assert 'os' in info
    assert 'python_version' in info
    assert 'hostname' in info


def test_system_diagnostic_collect_dependencies():
    """测试收集依赖版本"""
    diagnostic = SystemDiagnostic()
    versions = diagnostic.collect_dependency_versions(['pytest'])
    assert 'pytest' in versions
    assert versions['pytest'] is not None


def test_system_diagnostic_check_directories():
    """测试检查目录"""
    diagnostic = SystemDiagnostic()

    with tempfile.TemporaryDirectory() as tmpdir:
        result = diagnostic.check_config_directory(tmpdir)
        assert result['exists']
        assert 'issues' in result

        # 创建一个配置文件
        (Path(tmpdir) / 'config.yaml').write_text('test: 1')
        result = diagnostic.check_config_directory(tmpdir)
        assert len(result['files']) == 1


def test_system_diagnostic_generate_report():
    """测试生成诊断报告"""
    diagnostic = SystemDiagnostic()
    report = diagnostic.generate_report()

    assert 'timestamp' in report
    assert 'system_info' in report
    assert 'dependencies' in report
    assert 'config_directory' in report
    assert 'all_issues' in report


def test_system_diagnostic_export_markdown(tmp_path):
    """测试导出 Markdown 报告"""
    diagnostic = SystemDiagnostic()
    output_path = tmp_path / 'report.md'
    markdown = diagnostic.export_report_markdown(output_path)
    assert '# 系统诊断报告' in markdown
    assert output_path.exists()


def test_maintenance_clean_expired_logs(tmp_path):
    """测试清理过期日志"""
    maintenance = Maintenance()

    # 创建一些过期日志文件
    for i in range(5):
        log_file = tmp_path / f'test{i}.log'
        log_file.write_text('test')

    result = maintenance.clean_expired_logs(tmp_path, retention_days=0, dry_run=True)
    assert result['deleted_count'] == 5


def test_maintenance_estimate_size(tmp_path):
    """测试估算目录大小"""
    maintenance = Maintenance()

    for i in range(3):
        (tmp_path / f'file{i}.txt').write_text('x' * 100)

    size, count = maintenance.estimate_directory_size(tmp_path)
    assert count == 3
    assert size == 300


def test_maintenance_clean_temp_files(tmp_path):
    """测试清理临时文件"""
    maintenance = Maintenance()

    temp_dir = tmp_path / 'tmp'
    temp_dir.mkdir()
    for i in range(3):
        (temp_dir / f'tmp{i}').write_text('test')

    result = maintenance.clean_temp_files(temp_dir, max_age_hours=-1, dry_run=True)
    assert result['deleted_count'] == 3


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
