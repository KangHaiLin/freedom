#!/usr/bin/env python3
"""
同步股票基础信息到数据库
从AKShare获取全量股票基础信息并写入PostgreSQL
"""

import logging
import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from data_management.data_ingestion.akshare_fundamentals import AKShareFundamentalsCollector
from data_management.data_storage.storage_manager import storage_manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def main():
    """主函数"""
    print("=" * 60)
    print("开始同步股票基础信息...")
    print("=" * 60)

    # 初始化采集器
    akshare_config = {}  # 使用默认配置
    collector = AKShareFundamentalsCollector(akshare_config)

    # 获取股票基础信息
    print("\nStep 1: 从AKShare获取股票列表...")
    df = collector.get_stock_basic(list_status="L")

    if df.empty:
        print("ERROR: 获取股票列表为空！")
        sys.exit(1)

    print(f"成功获取 {len(df)} 只股票")
    print("\n前5条数据：")
    print(df[["stock_code", "name"]].head())

    # 获取PostgreSQL存储
    pg_storage = storage_manager.get_storage_by_type("postgresql")
    if not pg_storage:
        print("ERROR: 获取PostgreSQL存储失败！")
        sys.exit(1)

    # 检查表是否存在，如果不存在创建表
    table_name = "fundamental_stock_basic"

    if not pg_storage.table_exists(table_name):
        print(f"\nStep 2: 创建表 {table_name}...")
        # 定义表结构
        schema = {
            "stock_code": "VARCHAR(20)",
            "ts_code": "VARCHAR(20)",
            "name": "VARCHAR(100)",
            "fullname": "VARCHAR(200)",
            "enname": "VARCHAR(200)",
            "industry": "VARCHAR(50)",
            "market": "VARCHAR(20)",
            "list_date": "DATE",
            "delist_date": "DATE",
            "is_hs": "VARCHAR(10)",
        }
        pg_storage.create_table(table_name, schema, primary_key="stock_code")
        print(f"表 {table_name} 创建成功")
    else:
        print(f"\nStep 2: 表 {table_name} 已存在，跳过创建")
        # 查询现有记录数
        result = pg_storage.read(table_name)
        print(f"现有记录数：{len(result)}")

    # 写入数据
    print(f"\nStep 3: 写入数据到 {table_name}...")
    rows_written = pg_storage.write(table_name, df, if_exists="replace")
    print(f"写入完成，{rows_written} 条记录")

    # 验证写入
    result = pg_storage.read(table_name)
    print(f"\nStep 4: 验证数据，当前表总记录数：{len(result)}")
    print("\n前10条股票：")
    print(result[["stock_code", "name"]].head(10))

    storage_manager.disconnect_all()

    print("\n" + "=" * 60)
    print("✅ 股票基础信息同步完成！")
    print("=" * 60)
    print("\n现在你可以：")
    print("1. 刷新前端行情页面")
    print("2. 在搜索框中搜索股票代码或名称")
    print("3. 点击股票查看全量K线数据")


if __name__ == "__main__":
    main()
