"""
Unit tests for base_query.py
"""

import pandas as pd
import pytest
from datetime import datetime, date

from common.exceptions import QueryException
from data_management.data_query.base_query import QueryCondition, QueryResult, BaseQuery


class TestQueryCondition:
    """测试查询条件封装"""

    def test_default_init(self):
        """测试默认初始化"""
        cond = QueryCondition()
        assert cond.stock_codes is None
        assert cond.start_date is None
        assert cond.end_date is None
        assert cond.fields is None
        assert cond.filters is None
        assert cond.order_by is None
        assert cond.limit is None
        assert cond.offset is None

    def test_validate_valid(self):
        """测试验证合法条件"""
        cond = QueryCondition()
        cond.start_date = "2024-01-01"
        cond.end_date = "2024-01-31"
        cond.limit = 100
        cond.offset = 0
        assert cond.validate() is True

    def test_validate_start_after_end(self):
        """测试开始日期大于结束日期应该抛出异常"""
        cond = QueryCondition()
        cond.start_date = "2024-01-31"
        cond.end_date = "2024-01-01"
        with pytest.raises(QueryException, match="开始日期不能大于结束日期"):
            cond.validate()

    def test_validate_negative_limit(self):
        """测试负数limit应该抛出异常"""
        cond = QueryCondition()
        cond.limit = -10
        with pytest.raises(QueryException, match="limit不能为负数"):
            cond.validate()

    def test_validate_negative_offset(self):
        """测试负数offset应该抛出异常"""
        cond = QueryCondition()
        cond.offset = -5
        with pytest.raises(QueryException, match="offset不能为负数"):
            cond.validate()

    def test_to_dict(self):
        """测试转换为字典"""
        cond = QueryCondition()
        cond.stock_codes = ["600000.SH", "000001.SZ"]
        cond.start_date = "2024-01-01"
        cond.end_date = date(2024, 1, 31)
        cond.fields = ["trade_date", "open", "high", "low", "close"]
        cond.filters = {"data_type": "daily"}
        cond.limit = 100
        cond.offset = 10

        result = cond.to_dict()

        assert result["stock_codes"] == ["600000.SH", "000001.SZ"]
        assert result["start_date"] == "2024-01-01"
        assert result["end_date"] == "2024-01-31"
        assert result["fields"] == ["trade_date", "open", "high", "low", "close"]
        assert result["filters"] == {"data_type": "daily"}
        assert result["limit"] == 100
        assert result["offset"] == 10


class TestQueryResult:
    """测试查询结果封装"""

    def test_init_with_dataframe(self):
        """测试用DataFrame初始化"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = QueryResult(data=df, total=3, success=True, message="test")

        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == 3
        assert result.total == 3
        assert result.success is True
        assert result.message == "test"

    def test_init_with_list(self):
        """测试用列表初始化"""
        data = [{"a": 1, "b": 4}, {"a": 2, "b": 5}]
        result = QueryResult(data=data, total=2)

        assert result.data == data
        assert result.total == 2

    def test_to_dict_with_dataframe(self):
        """测试DataFrame转换为字典"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = QueryResult(data=df, total=3, success=True)
        dict_result = result.to_dict()

        assert dict_result["success"] is True
        assert len(dict_result["data"]) == 3
        assert dict_result["total"] == 3

    def test_to_df_with_dataframe(self):
        """测试DataFrame转换保持不变"""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        result = QueryResult(data=df)
        result_df = result.to_df()

        assert result_df is df
        assert len(result_df) == 3

    def test_to_df_with_list(self):
        """测试列表转换为DataFrame"""
        data = [{"a": 1, "b": 4}, {"a": 2, "b": 5}]
        result = QueryResult(data=data)
        result_df = result.to_df()

        assert isinstance(result_df, pd.DataFrame)
        assert len(result_df) == 2


class TestBaseQuery:
    """测试查询抽象基类的公共方法"""

    class ConcreteQuery(BaseQuery):
        """具体查询实现用于测试"""
        def query(self, condition):
            return QueryResult(data=pd.DataFrame())

    def test__apply_pagination(self):
        """测试分页应用"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({"id": list(range(100))})

        # offset=10, limit=20
        result = query._apply_pagination(df, 20, 10)
        assert len(result) == 20
        assert result.iloc[0]["id"] == 10
        assert result.iloc[-1]["id"] == 29

        # 只有offset
        result = query._apply_pagination(df, None, 50)
        assert len(result) == 50
        assert result.iloc[0]["id"] == 50

        # 只有limit
        result = query._apply_pagination(df, 10, None)
        assert len(result) == 10
        assert result.iloc[-1]["id"] == 9

    def test__apply_order_by_ascending(self):
        """测试升序排序"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({"value": [3, 1, 4, 2]})

        result = query._apply_order_by(df, "value")
        assert list(result["value"]) == [1, 2, 3, 4]

    def test__apply_order_by_descending(self):
        """测试降序排序（-前缀）"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({"value": [3, 1, 4, 2]})

        result = query._apply_order_by(df, "-value")
        assert list(result["value"]) == [4, 3, 2, 1]

    def test__apply_order_by_multiple(self):
        """测试多列排序"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({
            "category": ["B", "A", "B", "A"],
            "value": [2, 1, 1, 2],
        })

        result = query._apply_order_by(df, ["category", "value"])
        assert list(result["category"]) == ["A", "A", "B", "B"]
        assert list(result["value"]) == [1, 2, 1, 2]

    def test__apply_order_by_ignore_nonexistent(self):
        """测试忽略不存在的排序列"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({"value": [3, 1, 4, 2]})

        result = query._apply_order_by(df, "nonexistent")
        # 应该返回原数据
        assert len(result) == 4

    def test__apply_filters_list(self):
        """测试列表in过滤"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({"category": ["A", "B", "A", "C"], "value": [1, 2, 3, 4]})

        result = query._apply_filters(df, {"category": ["A", "C"]})
        assert len(result) == 3
        assert set(result["category"]) == {"A", "C"}

    def test__apply_filters_equal(self):
        """测试等值过滤"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({"category": ["A", "B", "A", "C"], "value": [1, 2, 3, 4]})

        result = query._apply_filters(df, {"category": "A"})
        assert len(result) == 2
        assert all(result["category"] == "A")

    def test__apply_filters_ignore_nonexistent(self):
        """测试忽略不存在的过滤列"""
        from unittest.mock import Mock
        query = self.ConcreteQuery(Mock())
        df = pd.DataFrame({"category": ["A", "B"], "value": [1, 2]})

        result = query._apply_filters(df, {"nonexistent": [1, 2]})
        assert len(result) == 2
