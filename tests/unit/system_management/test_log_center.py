"""
测试日志中心
"""
import tempfile
import os
from src.system_management.log_center import (
    LogLevel,
    LogRecord,
    LogManager,
    ConsoleLogger,
    FileLogger,
    StructuredLogger,
)


def test_log_level_from_string():
    """测试日志级别转换"""
    assert LogLevel.from_string('debug') == LogLevel.DEBUG
    assert LogLevel.from_string('INFO') == LogLevel.INFO
    assert LogLevel.from_string('warning') == LogLevel.WARNING
    assert LogLevel.from_string('error') == LogLevel.ERROR
    assert LogLevel.from_string('critical') == LogLevel.CRITICAL


def test_log_record_to_dict():
    """测试日志记录转换为字典"""
    import time
    record = LogRecord(
        level=LogLevel.INFO,
        message='test message',
        module='test',
        timestamp=time.time(),
        context={'key': 'value'},
        trace_id='trace-123',
    )
    data = record.to_dict()

    assert data['level'] == 'INFO'
    assert data['message'] == 'test message'
    assert data['module'] == 'test'
    assert data['context'] == {'key': 'value'}
    assert data['trace_id'] == 'trace-123'


def test_console_logger():
    """测试控制台日志"""
    logger = ConsoleLogger(min_level=LogLevel.INFO)
    import time
    record = LogRecord(
        level=LogLevel.INFO,
        message='test',
        module='test',
        timestamp=time.time(),
    )
    # 不抛出异常即可
    logger.log(record)
    assert logger.should_log(LogLevel.INFO)
    assert not logger.should_log(LogLevel.DEBUG)


def test_file_logger():
    """测试文件日志轮转"""
    with tempfile.TemporaryDirectory() as temp_dir:
        log_file = os.path.join(temp_dir, 'test.log')
        logger = FileLogger(
            log_file=log_file,
            min_level=LogLevel.DEBUG,
            max_size_bytes=1000,  # 很小，方便轮转
            retention_days=1,
        )

        import time
        record = LogRecord(
            level=LogLevel.INFO,
            message='test message',
            module='test',
            timestamp=time.time(),
        )

        # 写入一些日志
        for i in range(10):
            record.message = f'line {i}' + 'x' * 100
            logger.log(record)

        # 文件应该存在
        assert os.path.exists(log_file)
        # 有内容
        assert os.path.getsize(log_file) > 0


def test_structured_logger():
    """测试结构化日志"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as f:
        temp_path = f.name

    try:
        logger = StructuredLogger(output_file=temp_path)
        import time
        record = LogRecord(
            level=LogLevel.INFO,
            message='test structured log',
            module='test',
            timestamp=time.time(),
            context={'request_id': '12345'},
            trace_id='trace-abc',
        )
        logger.log(record)

        # 读取检查
        with open(temp_path, 'r') as f:
            line = f.readline()
            assert '"message":"test structured log"' in line
            assert '"request_id":"12345"' in line
            assert '"trace_id":"trace-abc"' in line
    finally:
        os.unlink(temp_path)


def test_log_manager():
    """测试日志管理器"""
    manager = LogManager()
    # 重新初始化
    manager._loggers = [ConsoleLogger(min_level=LogLevel.INFO)]
    manager._initialized = True

    manager.debug('debug message', 'test')  # 低于级别，应该过滤
    manager.info('info message', 'test')
    manager.warning('warning message', 'test')
    manager.error('error message', 'test')

    # 获取模块日志器
    logger = manager.get_logger('module')
    logger.info('module message')

    # 设置 trace_id
    manager.set_trace_id('trace-123')
    assert manager.get_trace_id() == 'trace-123'


def test_module_logger():
    """测试模块日志器"""
    manager = LogManager()
    logger = manager.get_logger('my_module')
    logger.info('test')  # 不抛出异常即可


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
