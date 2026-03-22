"""
规则管理器
管理规则的加载、存储、动态更新、版本管理
"""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.risk_management.base.base_rule import BaseRule, RuleLevel

from .rule import Rule, RuleVersion


class RuleManager:
    """
    规则管理器
    负责规则的增删改查、版本管理、灰度发布
    """

    def __init__(self):
        # 规则存储: rule_id -> Rule
        self._rules: Dict[str, Rule] = {}
        # 按规则组分组: rule_group -> List[rule_id]
        self._rules_by_group: Dict[str, List[str]] = defaultdict(list)
        # 版本历史: rule_id -> List[RuleVersion]
        self._versions: Dict[str, List[RuleVersion]] = defaultdict(list)

    def add_rule(self, rule: Rule, created_by: int, is_gray: bool = False) -> RuleVersion:
        """
        添加新规则或更新现有规则

        Args:
            rule: 规则对象
            created_by: 创建者ID
            is_gray: 是否是灰度发布

        Returns:
            新版本ID
        """
        # 创建版本记录
        version_id = str(uuid.uuid4())
        version = RuleVersion(
            version_id=version_id,
            rule_id=rule.rule_id,
            rule_content="",  # 对于函数式规则无法保存源码，这里留空
            rule_group=rule.rule_group,
            created_by=created_by,
        )

        # 保存规则
        if rule.rule_id in self._rules:
            # 更新现有规则
            old_rule = self._rules[rule.rule_id]
            # 从分组中移除旧版本
            if old_rule.rule_group in self._rules_by_group:
                if old_rule.rule_id in self._rules_by_group[old_rule.rule_group]:
                    self._rules_by_group[old_rule.rule_group].remove(old_rule.rule_id)
        self._rules[rule.rule_id] = rule

        # 添加到分组
        if rule.rule_id not in self._rules_by_group[rule.rule_group]:
            self._rules_by_group[rule.rule_group].append(rule.rule_id)

        # 保存版本
        self._versions[rule.rule_id].append(version)

        return version

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """获取规则"""
        return self._rules.get(rule_id)

    def delete_rule(self, rule_id: str) -> bool:
        """删除规则"""
        if rule_id not in self._rules:
            return False
        rule = self._rules[rule_id]
        if rule.rule_group in self._rules_by_group:
            if rule_id in self._rules_by_group[rule.rule_group]:
                self._rules_by_group[rule.rule_group].remove(rule_id)
        del self._rules[rule_id]
        return True

    def enable_rule(self, rule_id: str) -> bool:
        """启用规则"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.enable()
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """禁用规则"""
        rule = self.get_rule(rule_id)
        if rule:
            rule.disable()
            return True
        return False

    def get_rules_by_group(self, rule_group: str) -> List[Rule]:
        """获取规则组中所有启用的规则，按优先级排序"""
        if rule_group not in self._rules_by_group:
            return []
        rules = [self._rules[rid] for rid in self._rules_by_group[rule_group] if self._rules[rid].is_enabled()]
        # 按优先级排序（数字越小优先级越高）
        rules.sort(key=lambda r: r.priority)
        return rules

    def get_all_rules(self) -> List[Rule]:
        """获取所有规则"""
        return list(self._rules.values())

    def get_all_groups(self) -> List[str]:
        """获取所有规则组"""
        return list(self._rules_by_group.keys())

    def get_version_history(self, rule_id: str) -> List[RuleVersion]:
        """获取规则版本历史"""
        return self._versions.get(rule_id, [])

    def rollback(self, rule_id: str, version_id: str) -> bool:
        """回滚到指定版本
        注意：由于函数无法序列化，回滚需要重新编译规则内容
        """
        versions = self.get_version_history(rule_id)
        for v in versions:
            if v.version_id == version_id:
                # 这里需要外部重新加载规则内容，仅记录版本信息
                return True
        return False

    def load_gray_rule(
        self,
        rule: Rule,
        created_by: int,
        gray_percentage: int,
        gray_users: Optional[List[int]] = None,
    ) -> RuleVersion:
        """加载灰度版本规则"""
        version_id = str(uuid.uuid4())
        version = RuleVersion(
            version_id=version_id,
            rule_id=rule.rule_id,
            rule_content="",
            rule_group=rule.rule_group,
            created_by=created_by,
            gray_percentage=gray_percentage,
            gray_users=gray_users or [],
        )
        # 保存版本
        self._versions[rule.rule_id].append(version)
        return version

    def count_rules(self) -> Dict[str, Any]:
        """获取规则统计"""
        total = len(self._rules)
        enabled = sum(1 for r in self._rules.values() if r.is_enabled())
        by_group = {g: len(ids) for g, ids in self._rules_by_group.items()}
        return {
            "total": total,
            "enabled": enabled,
            "disabled": total - enabled,
            "by_group": by_group,
        }

    def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        stats = self.count_rules()
        return {
            "status": "ok",
            "stats": stats,
        }
