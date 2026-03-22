"""
风险事件存储
存储所有风险事件和违规记录，支持审计追溯
"""

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.risk_management.rule_engine.rule_result import RuleViolation


@dataclass
class RiskEvent:
    """风险事件"""

    event_id: int
    event_type: str
    event_level: str
    rule_id: Optional[str]
    user_id: Optional[int]
    ts_code: Optional[str]
    message: str
    details: Dict[str, Any]
    handled: bool
    handled_by: Optional[int]
    handled_note: Optional[str]
    handled_at: Optional[datetime]
    occurred_at: datetime
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = asdict(self)
        # 转换datetime为字符串
        if self.handled_at:
            result["handled_at"] = self.handled_at.isoformat()
        result["occurred_at"] = self.occurred_at.isoformat()
        result["created_at"] = self.created_at.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskEvent":
        """从字典创建"""
        if data.get("handled_at"):
            data["handled_at"] = datetime.fromisoformat(data["handled_at"])
        data["occurred_at"] = datetime.fromisoformat(data["occurred_at"])
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        return cls(**data)


class RiskEventStore:
    """
    风险事件存储
    存储所有风险事件，支持查询、统计、处理跟踪
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化风险事件存储

        Args:
            storage_path: 存储文件路径
        """
        if storage_path is None:
            storage_path = "data/risk_events.jsonl"
        self._storage_path = Path(storage_path)
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)

        # 确保文件存在
        if not self._storage_path.exists():
            self._storage_path.touch()

        self._events: List[RiskEvent] = []
        self._next_id = 1
        self._load_from_file()

    def add_event(
        self,
        event_type: str,
        event_level: str,
        message: str,
        rule_id: Optional[str] = None,
        user_id: Optional[int] = None,
        ts_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        添加风险事件

        Args:
            event_type: 事件类型
            event_level: 事件级别
            message: 事件消息
            rule_id: 规则ID
            user_id: 用户ID
            ts_code: 股票代码
            details: 详情

        Returns:
            事件ID
        """
        event_id = self._next_id
        self._next_id += 1

        event = RiskEvent(
            event_id=event_id,
            event_type=event_type,
            event_level=event_level,
            rule_id=rule_id,
            user_id=user_id,
            ts_code=ts_code,
            message=message,
            details=details or {},
            handled=False,
            handled_by=None,
            handled_note=None,
            handled_at=None,
            occurred_at=datetime.now(),
            created_at=datetime.now(),
        )

        self._events.append(event)
        self._append_to_file(event)
        return event_id

    def add_from_violation(
        self,
        violation: RuleViolation,
        event_type: str,
        user_id: Optional[int] = None,
        ts_code: Optional[str] = None,
    ) -> int:
        """从规则违规创建事件"""
        return self.add_event(
            event_type=event_type,
            event_level=violation.level.value,
            message=violation.message,
            rule_id=violation.rule_id,
            user_id=user_id,
            ts_code=ts_code,
            details=violation.details,
        )

    def mark_handled(
        self,
        event_id: int,
        handled_by: int,
        handled_note: str,
    ) -> bool:
        """标记事件已处理"""
        for event in self._events:
            if event.event_id == event_id:
                event.handled = True
                event.handled_by = handled_by
                event.handled_note = handled_note
                event.handled_at = datetime.now()
                self._save_to_file()
                return True
        return False

    def get_event(self, event_id: int) -> Optional[RiskEvent]:
        """获取事件"""
        for event in self._events:
            if event.event_id == event_id:
                return event
        return None

    def query_events(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        event_type: Optional[str] = None,
        event_level: Optional[str] = None,
        rule_id: Optional[str] = None,
        user_id: Optional[int] = None,
        handled: Optional[bool] = None,
    ) -> List[RiskEvent]:
        """查询风险事件"""
        results = []
        for event in self._events:
            if start_date and event.occurred_at.date() < start_date:
                continue
            if end_date and event.occurred_at.date() > end_date:
                continue
            if event_type and event.event_type != event_type:
                continue
            if event_level and event.event_level != event_level:
                continue
            if rule_id and event.rule_id != rule_id:
                continue
            if user_id and event.user_id != user_id:
                continue
            if handled is not None and event.handled != handled:
                continue
            results.append(event)
        return results

    def get_statistics(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """获取事件统计"""
        events = self.query_events(start_date, end_date)
        if not events:
            return {
                "total_events": 0,
                "by_level": {},
                "by_type": {},
                "unhandled": 0,
            }

        by_level: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        unhandled = 0

        for event in events:
            level = event.event_level
            by_level[level] = by_level.get(level, 0) + 1
            etype = event.event_type
            by_type[etype] = by_type.get(etype, 0) + 1
            if not event.handled:
                unhandled += 1

        return {
            "total_events": len(events),
            "by_level": by_level,
            "by_type": by_type,
            "unhandled": unhandled,
        }

    def count_events(self) -> int:
        """获取事件总数"""
        return len(self._events)

    def _load_from_file(self) -> None:
        """从文件加载"""
        if not self._storage_path.exists():
            return

        count = 0
        with open(self._storage_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    event = RiskEvent.from_dict(data)
                    self._events.append(event)
                    if event.event_id >= self._next_id:
                        self._next_id = event.event_id + 1
                    count += 1
                except Exception as e:
                    import logging

                    logging.warning(f"Failed to load risk event: {e}, line: {line[:100]}")
                    continue

    def _append_to_file(self, event: RiskEvent) -> None:
        """追加到文件"""
        with open(self._storage_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def _save_to_file(self) -> None:
        """全量保存到文件（修改后）"""
        with open(self._storage_path, "w", encoding="utf-8") as f:
            for event in self._events:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "status": "ok",
            "total_events": self.count_events(),
            "storage_path": str(self._storage_path),
            "file_exists": self._storage_path.exists(),
            "file_size_bytes": self._storage_path.stat().st_size if self._storage_path.exists() else 0,
        }
