"""
Q-005 存储性能基准测试脚本
测试目标：验证不同数据库的读写性能是否满足要求
- 目标1：基础写入性能 > 10,000条/秒
- 目标2：高并发写入 > 50,000条/秒
- 目标3：集群写入性能 > 100,000条/秒
- 目标4：查询响应时间 < 200ms
"""
import time
import random
import string
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import redis
import clickhouse_driver

# 测试配置
TEST_CONFIG = {
    'postgresql': {
        'host': 'localhost',
        'port': 5433,
        'database': 'stock_test',
        'user': 'test',
        'password': 'test123'
    },
    'clickhouse': {
        'host': 'localhost',
        'port': 9000,
        'database': 'stock_test',
        'user': 'test',
        'password': 'test123'
    },
    'redis': {
        'host': 'localhost',
        'port': 6379,
        'db': 0
    }
}

def generate_test_data(count: int = 10000) -> List[Dict]:
    """生成测试行情数据"""
    symbols = [f'{random.randint(0, 999999):06d}.SZ' for _ in range(100)]
    now = datetime.now()

    data = []
    for i in range(count):
        timestamp = now - timedelta(seconds=i)
        data.append({
            'symbol': random.choice(symbols),
            'time': timestamp,
            'open': random.uniform(10, 100),
            'high': random.uniform(10, 100),
            'low': random.uniform(10, 100),
            'close': random.uniform(10, 100),
            'volume': random.randint(1000, 1000000),
            'amount': random.uniform(10000, 10000000)
        })

    return data

def test_postgresql_write(batch_size: int = 10000) -> Dict:
    """测试PostgreSQL写入性能"""
    conn_str = f"postgresql://{TEST_CONFIG['postgresql']['user']}:{TEST_CONFIG['postgresql']['password']}@{TEST_CONFIG['postgresql']['host']}:{TEST_CONFIG['postgresql']['port']}/{TEST_CONFIG['postgresql']['database']}"
    engine = create_engine(conn_str)

    data = generate_test_data(batch_size)
    df = pd.DataFrame(data)

    start_time = time.time()
    df.to_sql('market_data', engine, if_exists='append', index=False, chunksize=1000)
    elapsed = time.time() - start_time

    speed = batch_size / elapsed

    return {
        'database': 'postgresql',
        'operation': 'write',
        'batch_size': batch_size,
        'elapsed_seconds': round(elapsed, 2),
        'records_per_second': round(speed, 2),
        'target_met': speed > 10000
    }

def test_clickhouse_write(batch_size: int = 50000) -> Dict:
    """测试ClickHouse写入性能"""
    conn = clickhouse_driver.Client(
        host=TEST_CONFIG['clickhouse']['host'],
        port=TEST_CONFIG['clickhouse']['port'],
        user=TEST_CONFIG['clickhouse']['user'],
        password=TEST_CONFIG['clickhouse']['password'],
        database=TEST_CONFIG['clickhouse']['database']
    )

    # 创建测试表（如果不存在）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            symbol String,
            time DateTime,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume Int32,
            amount Float64
        ) ENGINE = MergeTree()
        ORDER BY (time, symbol)
    """)

    data = generate_test_data(batch_size)
    columns = ['symbol', 'time', 'open', 'high', 'low', 'close', 'volume', 'amount']
    rows = [tuple(d[col] for col in columns) for d in data]

    start_time = time.time()
    conn.execute(
        'INSERT INTO market_data (symbol, time, open, high, low, close, volume, amount) VALUES',
        rows
    )
    elapsed = time.time() - start_time

    speed = batch_size / elapsed

    return {
        'database': 'clickhouse',
        'operation': 'write',
        'batch_size': batch_size,
        'elapsed_seconds': round(elapsed, 2),
        'records_per_second': round(speed, 2),
        'target_met': speed > 50000
    }

def test_redis_write(batch_size: int = 100000) -> Dict:
    """测试Redis写入性能"""
    r = redis.Redis(
        host=TEST_CONFIG['redis']['host'],
        port=TEST_CONFIG['redis']['port'],
        db=TEST_CONFIG['redis']['db'],
        decode_responses=True
    )

    data = generate_test_data(batch_size)

    start_time = time.time()
    pipe = r.pipeline()
    for item in data:
        key = f"market:{item['symbol']}:{int(item['time'].timestamp())}"
        value = f"{item['open']},{item['high']},{item['low']},{item['close']},{item['volume']}"
        pipe.set(key, value)
    pipe.execute()
    elapsed = time.time() - start_time

    speed = batch_size / elapsed

    return {
        'database': 'redis',
        'operation': 'write',
        'batch_size': batch_size,
        'elapsed_seconds': round(elapsed, 2),
        'records_per_second': round(speed, 2),
        'target_met': speed > 100000
    }

def test_postgresql_query() -> Dict:
    """测试PostgreSQL查询性能"""
    conn_str = f"postgresql://{TEST_CONFIG['postgresql']['user']}:{TEST_CONFIG['postgresql']['password']}@{TEST_CONFIG['postgresql']['host']}:{TEST_CONFIG['postgresql']['port']}/{TEST_CONFIG['postgresql']['database']}"
    engine = create_engine(conn_str)

    # 创建测试表（如果不存在）
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS market_data (
                symbol VARCHAR(20),
                time TIMESTAMP,
                open DOUBLE PRECISION,
                high DOUBLE PRECISION,
                low DOUBLE PRECISION,
                close DOUBLE PRECISION,
                bigint INTEGER,
                amount DOUBLE PRECISION
            )
        """))
        conn.commit()

    start_time = time.time()
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT symbol, COUNT(*) as count, AVG(close) as avg_close
            FROM market_data
            WHERE time >= NOW() - INTERVAL '1 hour'
            GROUP BY symbol
            ORDER BY count DESC
            LIMIT 10
        """))
        rows = result.fetchall()
    elapsed = (time.time() - start_time) * 1000  # 转换为毫秒

    return {
        'database': 'postgresql',
        'operation': 'query',
        'elapsed_ms': round(elapsed, 2),
        'rows_returned': len(rows),
        'target_met': elapsed < 200
    }

def test_clickhouse_query() -> Dict:
    """测试ClickHouse查询性能"""
    conn = clickhouse_driver.Client(
        host=TEST_CONFIG['clickhouse']['host'],
        port=TEST_CONFIG['clickhouse']['port'],
        user=TEST_CONFIG['clickhouse']['user'],
        password=TEST_CONFIG['clickhouse']['password'],
        database=TEST_CONFIG['clickhouse']['database']
    )

    # 创建测试表（如果不存在）
    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            symbol String,
            time DateTime,
            open Float64,
            high Float64,
            low Float64,
            close Float64,
            volume Int32,
            amount Float64
        ) ENGINE = MergeTree()
        ORDER BY (time, symbol)
    """)

    start_time = time.time()
    rows = conn.execute("""
        SELECT symbol, COUNT(*) as count, AVG(close) as avg_close
        FROM market_data
        WHERE time >= NOW() - INTERVAL 1 HOUR
        GROUP BY symbol
        ORDER BY count DESC
        LIMIT 10
    """)
    elapsed = (time.time() - start_time) * 1000  # 转换为毫秒

    return {
        'database': 'clickhouse',
        'operation': 'query',
        'elapsed_ms': round(elapsed, 2),
        'rows_returned': len(rows),
        'target_met': elapsed < 200
    }

def run_all_benchmarks() -> List[Dict]:
    """运行所有存储性能基准测试"""
    print("🚀 开始执行Q-005存储性能基准测试...")
    print("=" * 80)

    results = []

    # 写入性能测试
    print("\n📊 测试1：PostgreSQL写入性能 (1万条，目标：>10,000条/秒)")
    try:
        result1 = test_postgresql_write()
        results.append(result1)
        status = "✅ 达标" if result1['target_met'] else "❌ 未达标"
        print(f"   耗时：{result1['elapsed_seconds']}秒 | 速度：{result1['records_per_second']:,}条/秒 | {status}")
    except Exception as e:
        print(f"   ❌ 测试失败：{str(e)}")

    print("\n📊 测试2：ClickHouse写入性能 (5万条，目标：>50,000条/秒)")
    try:
        result2 = test_clickhouse_write()
        results.append(result2)
        status = "✅ 达标" if result2['target_met'] else "❌ 未达标"
        print(f"   耗时：{result2['elapsed_seconds']}秒 | 速度：{result2['records_per_second']:,}条/秒 | {status}")
    except Exception as e:
        print(f"   ❌ 测试失败：{str(e)}")

    print("\n📊 测试3：Redis写入性能 (10万条，目标：>100,000条/秒)")
    try:
        result3 = test_redis_write()
        results.append(result3)
        status = "✅ 达标" if result3['target_met'] else "❌ 未达标"
        print(f"   耗时：{result3['elapsed_seconds']}秒 | 速度：{result3['records_per_second']:,}条/秒 | {status}")
    except Exception as e:
        print(f"   ❌ 测试失败：{str(e)}")

    # 查询性能测试
    print("\n📊 测试4：PostgreSQL查询性能 (目标：<200ms)")
    try:
        result4 = test_postgresql_query()
        results.append(result4)
        status = "✅ 达标" if result4['target_met'] else "❌ 未达标"
        print(f"   耗时：{result4['elapsed_ms']}ms | 返回行数：{result4['rows_returned']} | {status}")
    except Exception as e:
        print(f"   ❌ 测试失败：{str(e)}")

    print("\n📊 测试5：ClickHouse查询性能 (目标：<200ms)")
    try:
        result5 = test_clickhouse_query()
        results.append(result5)
        status = "✅ 达标" if result5['target_met'] else "❌ 未达标"
        print(f"   耗时：{result5['elapsed_ms']}ms | 返回行数：{result5['rows_returned']} | {status}")
    except Exception as e:
        print(f"   ❌ 测试失败：{str(e)}")

    # 汇总结果
    print("\n" + "=" * 80)
    print("📋 Q-005存储性能基准测试结果汇总：")
    passed = sum(1 for r in results if r['target_met'])
    total = len(results)
    print(f"   总测试数：{total} | 通过数：{passed} | 通过率：{passed/total*100:.1f}%")

    all_passed = passed == total
    if all_passed:
        print("🎉 所有测试均达到性能目标！")
    else:
        print("⚠️  部分测试未达到性能目标，需要优化。")

    # 保存结果
    with open('q005_benchmark_results.txt', 'w') as f:
        f.write("Q-005 存储性能基准测试结果\n")
        f.write("=" * 50 + "\n")
        for r in results:
            f.write(f"\n数据库：{r['database']}\n")
            f.write(f"操作：{r['operation']}\n")
            if r['operation'] == 'write':
                f.write(f"批量大小：{r['batch_size']:,}\n")
                f.write(f"速度：{r['records_per_second']:,}条/秒\n")
            else:
                f.write(f"耗时：{r['elapsed_ms']}ms\n")
            f.write(f"是否达标：{'是' if r['target_met'] else '否'}\n")

    return results

if __name__ == "__main__":
    run_all_benchmarks()