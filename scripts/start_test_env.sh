#!/bin/bash
# 启动测试环境脚本

echo "🚀 启动量化交易系统测试环境..."

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose 未安装，请先安装docker-compose"
    exit 1
fi

# 启动服务
docker compose -f docker-compose.test.yml up -d

echo "⏳ 等待服务启动..."

# 等待所有服务健康检查通过
until docker compose -f docker-compose.test.yml ps | grep -E "postgres.*healthy|clickhouse.*healthy|redis.*healthy" | wc -l | grep -q 3; do
    echo "等待服务启动中..."
    sleep 2
done

echo "✅ 所有测试服务启动成功！"
echo ""
echo "服务地址："
echo "PostgreSQL: localhost:5432"
echo "ClickHouse: localhost:8123, localhost:9000"
echo "Redis: localhost:6379"
echo ""
echo "数据库信息："
echo "数据库名：stock_test"
echo "用户名：test"
echo "密码：test123"
echo ""
echo "运行测试命令："
echo "pytest tests/unit/ -v"
echo ""
echo "停止测试环境命令："
echo "docker compose -f docker-compose.test.yml down"
