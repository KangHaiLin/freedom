"""
操作日志记录器
记录所有风控操作，满足合规审计要求
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
from pathlib import Path


class OperationType:
    """操作类型常量"""
    RULE_CREATE = "rule_create"
    RULE_UPDATE = "rule_update"
    RULE_DELETE = "rule_delete"
    RULE_ENABLE = "rule_enable"
    RULE_DISABLE = "rule_disable"
    RISK_CHECK = "risk_check"
    RISK_ALERT = "risk_alert"
    VIOLATION_HANDLE = "violation_handle"
    LIMIT_UPDATE = "limit_update"
    REPORT_GENERATE = "report_generate"


class OperationLog:
    """操作日志记录"""

    def __init__(
        self,
        log_id: int,
        operation_type: str,
        operator_id: int,
        operation_time: datetime,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
    ):
        self.log_id = log_id
        self.operation_type = operation_type
        self.operator_id = operator_id
        self.operation_time = operation_time
        self.details = details
        self.ip_address = ip_address

    def to_json(self) -> str:
        """序列化为JSON"""
        return json.dumps({
            'log_id': self.log_id,
            'operation_type': self.operation_type,
            'operator_id': self.operator_id,
            'operation_time': self.operation_time.isoformat(),
            'details': self.details,
            'ip_address': self.ip_address,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, json_str: str) -> 'OperationLog':
        """从JSON反序列化"""
        data = json.loads(json_str)
        return cls(
            log_id=data['log_id'],
            operation_type=data['operation_type'],
            operator_id=data['operator_id'],
            operation_time=datetime.fromisoformat(data['operation_time']),
            details=data['details'],
            ip_address=data.get('ip_address'),
        )


class OperationLogger:
    """
    操作日志记录器
    所有风控操作必须记录日志，不可篡改，满足合规审计要求
    """

    def __init__(
        self,
        log_file_path: Optional[str] = None,
        enable_console: bool = True,
    ):
        """
        初始化操作日志记录器

        Args:
            log_file_path: 日志文件路径，None使用默认路径
            enable_console: 是否输出到控制台
        """
        if log_file_path is None:
            log_file_path = 'logs/risk_operations.log'
        self._log_path = Path(log_file_path)
        self._log_path.parent.mkdir(parents=True, exist_ok=True)

        self._next_id = 1
        self._logs: List[OperationLog] = []
        self._enable_console = enable_console

        # 直接打开文件，不使用logging避免格式问题
        self._ensure_file_exists()

    def log(
        self,
        operation_type: str,
        operator_id: int,
        details: Dict[str, Any],
        ip_address: Optional[str] = None,
    ) -> int:
        """
        记录操作日志

        Args:
            operation_type: 操作类型
            operator_id: 操作人ID
            details: 操作详情
            ip_address: IP地址

        Returns:
            日志ID
        """
        log_id = self._next_id
        self._next_id += 1

        log = OperationLog(
            log_id=log_id,
            operation_type=operation_type,
            operator_id=operator_id,
            operation_time=datetime.now(),
            details=details,
            ip_address=ip_address,
        )

        self._logs.append(log)
        # 写入文件，JSON格式一行一条
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(log.to_json() + '\n')

        if self._enable_console:
            print(f"[AUDIT] {log.operation_type} by {log.operator_id}: {details}")

        return log_id

    def get_recent_logs(
        self,
        count: int = 100,
        operation_type: Optional[str] = None,
    ) -> List[OperationLog]:
        """获取最近的日志"""
        logs = self._logs[-count:]
        if operation_type:
            logs = [l for l in logs if l.operation_type == operation_type]
        return logs

    def query_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        operation_type: Optional[str] = None,
        operator_id: Optional[int] = None,
    ) -> List[OperationLog]:
        """查询日志"""
        results = []
        for log in self._logs:
            if start_time and log.operation_time < start_time:
                continue
            if end_time and log.operation_time > end_time:
                continue
            if operation_type and log.operation_type != operation_type:
                continue
            if operator_id and log.operator_id != operator_id:
                continue
            results.append(log)
        return results

    def load_from_file(self) -> int:
        """从文件加载历史日志"""
        if not self._log_path.exists():
            return 0

        count = 0
        with open(self._log_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 提取JSON部分（logging会在开头加时间等）
                # 如果直接用logging保存，这里需要解析
                try:
                    log = OperationLog.from_json(line.split(' - ')[-1])
                except:
                    try:
                        log = OperationLog.from_json(line)
                    except:
                        continue
                self._logs.append(log)
                if log.log_id >= self._next_id:
                    self._next_id = log.log_id + 1
                count += 1
        return count

    def _ensure_file_exists(self):
        """确保文件存在"""
        if not self._log_path.exists():
            # 创建空文件
            self._log_path.touch()
        else:
            # 加载已有内容
            self.load_from_file()

    def count_logs(self) -> int:
        """获取日志总数"""
        return len(self._logs)

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            'status': 'ok',
            'total_logs': self.count_logs(),
            'log_file': str(self._log_path),
            'log_file_exists': self._log_path.exists(),
        }
