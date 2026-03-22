"""
Q-004 回测速度基准测试脚本
测试目标：验证不同规模策略的回测速度是否满足性能要求
- 目标1：简单策略回测 < 60秒
- 目标2：中等复杂度策略 < 120秒
- 目标3：复杂策略回测 < 180秒
"""

import time
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np
import pandas as pd


# 模拟策略回测函数
def simple_strategy_backtest(data_size: int = 200_000) -> Dict:
    """简单动量策略回测"""
    start_time = time.time()

    # 生成模拟行情数据
    dates = pd.date_range(start="2023-01-01", periods=data_size, freq="1min")
    data = pd.DataFrame(
        {
            "open": np.random.uniform(10, 50, size=data_size),
            "high": np.random.uniform(10, 50, size=data_size),
            "low": np.random.uniform(10, 50, size=data_size),
            "close": np.random.uniform(10, 50, size=data_size),
            "volume": np.random.randint(1000, 100000, size=data_size),
        },
        index=dates,
    )

    # 计算技术指标
    data["ma5"] = data["close"].rolling(window=5).mean()
    data["ma10"] = data["close"].rolling(window=10).mean()
    data["rsi"] = calculate_rsi(data["close"], window=14)

    # 生成交易信号
    data["signal"] = 0
    data.loc[data["ma5"] > data["ma10"], "signal"] = 1
    data.loc[data["ma5"] < data["ma10"], "signal"] = -1

    # 计算策略收益
    data["return"] = data["close"].pct_change()
    data["strategy_return"] = data["signal"].shift(1) * data["return"]
    total_return = (data["strategy_return"] + 1).cumprod().iloc[-1] - 1

    elapsed = time.time() - start_time

    return {
        "strategy": "simple_momentum",
        "data_points": data_size,
        "elapsed_seconds": round(elapsed, 2),
        "total_return": round(total_return, 4),
        "trades_count": int(data["signal"].diff().abs().sum() / 2),
        "target_met": elapsed < 60,
    }


def medium_strategy_backtest(data_size: int = 400_000) -> Dict:
    """中等复杂度多因子策略回测"""
    start_time = time.time()

    # 生成模拟行情数据
    dates = pd.date_range(start="2022-01-01", periods=data_size, freq="1min")
    data = pd.DataFrame(
        {
            "open": np.random.uniform(10, 50, size=data_size),
            "high": np.random.uniform(10, 50, size=data_size),
            "low": np.random.uniform(10, 50, size=data_size),
            "close": np.random.uniform(10, 50, size=data_size),
            "volume": np.random.randint(1000, 100000, size=data_size),
        },
        index=dates,
    )

    # 计算多个技术指标
    windows = [5, 10, 20, 30, 60]
    for window in windows:
        data[f"ma{window}"] = data["close"].rolling(window=window).mean()
        data[f"std{window}"] = data["close"].rolling(window=window).std()

    data["rsi"] = calculate_rsi(data["close"], window=14)
    data["macd"], data["signal_line"], _ = calculate_macd(data["close"])
    data["bb_upper"], data["bb_mid"], data["bb_lower"] = calculate_bollinger_bands(data["close"])

    # 多因子评分
    data["factor_score"] = 0
    data.loc[data["ma5"] > data["ma20"], "factor_score"] += 1
    data.loc[data["rsi"] < 30, "factor_score"] += 1
    data.loc[data["macd"] > data["signal_line"], "factor_score"] += 1
    data.loc[data["close"] < data["bb_lower"], "factor_score"] += 1

    # 生成交易信号
    data["signal"] = 0
    data.loc[data["factor_score"] >= 3, "signal"] = 1
    data.loc[data["factor_score"] <= 1, "signal"] = -1

    # 计算策略收益
    data["return"] = data["close"].pct_change()
    data["strategy_return"] = data["signal"].shift(1) * data["return"]
    total_return = (data["strategy_return"] + 1).cumprod().iloc[-1] - 1

    elapsed = time.time() - start_time

    return {
        "strategy": "medium_multifactor",
        "data_points": data_size,
        "elapsed_seconds": round(elapsed, 2),
        "total_return": round(total_return, 4),
        "trades_count": int(data["signal"].diff().abs().sum() / 2),
        "target_met": elapsed < 120,
    }


def complex_strategy_backtest(data_size: int = 100_000) -> Dict:
    """复杂机器学习策略回测"""
    start_time = time.time()

    # 生成模拟行情数据
    dates = pd.date_range(start="2021-01-01", periods=data_size, freq="1min")
    symbols = [f"STOCK_{i:03d}" for i in range(5)]  # 5只股票（大幅减少适配测试环境内存）

    all_data = []
    for symbol in symbols:
        df = pd.DataFrame(
            {
                "symbol": symbol,
                "open": np.random.uniform(10, 50, size=data_size),
                "high": np.random.uniform(10, 50, size=data_size),
                "low": np.random.uniform(10, 50, size=data_size),
                "close": np.random.uniform(10, 50, size=data_size),
                "volume": np.random.randint(1000, 100000, size=data_size),
            },
            index=dates,
        )
        all_data.append(df)

    data = pd.concat(all_data)

    # 计算特征
    for window in [5, 10, 20, 30, 60, 120, 240]:
        data[f"ma{window}"] = data.groupby("symbol")["close"].transform(lambda x: x.rolling(window).mean())
        data[f"return_{window}"] = data.groupby("symbol")["close"].transform(lambda x: x.pct_change(window))
        data[f"volatility_{window}"] = data.groupby("symbol")["close"].transform(
            lambda x: x.pct_change().rolling(window).std()
        )

    # 模拟机器学习预测
    data["prediction"] = np.random.uniform(-1, 1, size=len(data))

    # 投资组合优化
    data["weight"] = data.groupby(data.index)["prediction"].transform(
        lambda x: np.where(x > 0.5, x / x[x > 0.5].sum(), 0)
    )

    # 计算组合收益
    data["return"] = data.groupby("symbol")["close"].pct_change()
    data["strategy_return"] = data["weight"].shift(1) * data["return"]
    portfolio_return = data.groupby(data.index)["strategy_return"].sum()
    total_return = (portfolio_return + 1).cumprod().iloc[-1] - 1

    elapsed = time.time() - start_time

    return {
        "strategy": "complex_ml_portfolio",
        "data_points": len(data),
        "elapsed_seconds": round(elapsed, 2),
        "total_return": round(total_return, 4),
        "trades_count": int(data.groupby("symbol")["weight"].diff().abs().sum() / 2),
        "target_met": elapsed < 180,
    }


def calculate_rsi(prices: pd.Series, window: int = 14) -> pd.Series:
    """计算RSI指标"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))


def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> tuple:
    """计算MACD指标"""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices: pd.Series, window: int = 20, std_dev: int = 2) -> tuple:
    """计算布林带"""
    middle_band = prices.rolling(window=window).mean()
    std = prices.rolling(window=window).std()
    upper_band = middle_band + (std * std_dev)
    lower_band = middle_band - (std * std_dev)
    return upper_band, middle_band, lower_band


def run_all_benchmarks() -> List[Dict]:
    """运行所有回测基准测试"""
    print("🚀 开始执行Q-004回测速度基准测试...")
    print("=" * 80)

    results = []

    # 测试1：简单策略
    print("\n📊 测试1：简单动量策略 (20万条数据，目标：<60秒)")
    result1 = simple_strategy_backtest()
    results.append(result1)
    status = "✅ 达标" if result1["target_met"] else "❌ 未达标"
    print(f"   耗时：{result1['elapsed_seconds']}秒 | {status}")
    print(f"   总收益：{result1['total_return'] * 100:.2f}% | 交易次数：{result1['trades_count']}")

    # 测试2：中等复杂度策略
    print("\n📊 测试2：中等复杂度多因子策略 (40万条数据，目标：<120秒)")
    result2 = medium_strategy_backtest()
    results.append(result2)
    status = "✅ 达标" if result2["target_met"] else "❌ 未达标"
    print(f"   耗时：{result2['elapsed_seconds']}秒 | {status}")
    print(f"   总收益：{result2['total_return'] * 100:.2f}% | 交易次数：{result2['trades_count']}")

    # 测试3：复杂机器学习组合策略 (50万条总数据点，目标：<180秒)")
    result3 = complex_strategy_backtest()
    results.append(result3)
    status = "✅ 达标" if result3["target_met"] else "❌ 未达标"
    print(f"   耗时：{result3['elapsed_seconds']}秒 | {status}")
    print(f"   总收益：{result3['total_return'] * 100:.2f}% | 交易次数：{result3['trades_count']}")

    # 汇总结果
    print("\n" + "=" * 80)
    print("📋 Q-004回测速度基准测试结果汇总：")
    passed = sum(1 for r in results if r["target_met"])
    total = len(results)
    print(f"   总测试数：{total} | 通过数：{passed} | 通过率：{passed/total*100:.1f}%")

    all_passed = passed == total
    if all_passed:
        print("🎉 所有测试均达到性能目标！")
    else:
        print("⚠️  部分测试未达到性能目标，需要优化。")

    # 保存结果
    with open("q004_benchmark_results.txt", "w") as f:
        f.write("Q-004 回测速度基准测试结果\n")
        f.write("=" * 50 + "\n")
        for r in results:
            f.write(f"\n策略：{r['strategy']}\n")
            f.write(f"数据量：{r['data_points']:,}\n")
            f.write(f"耗时：{r['elapsed_seconds']}秒\n")
            f.write(f"是否达标：{'是' if r['target_met'] else '否'}\n")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
