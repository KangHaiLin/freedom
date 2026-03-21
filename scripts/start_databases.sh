#!/bin/bash
#
# 启动项目所有依赖的数据库服务
# 使用 docker-compose 启动 PostgreSQL, ClickHouse, Redis
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "============================================"
echo "  启动项目数据库服务"
echo "  PostgreSQL: localhost:5433"
echo "  ClickHouse: localhost:9000 / http://localhost:8123"
echo "  Redis: localhost:6379"
echo "============================================"
echo ""

# 检查docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ 错误: docker 未安装，请先安装 docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ 错误: docker-compose 未安装，请先安装 docker-compose"
    exit 1
fi

echo "🚀 正在启动数据库服务..."
echo ""

# 优先使用新的 docker compose 插件版
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE="docker-compose"
else
    echo "❌ 错误: docker compose 未找到，请先安装 docker 和 docker compose"
    exit 1
fi

$DOCKER_COMPOSE -f docker-compose.test.yml up -d

echo ""
echo "⏳ 等待数据库启动完成..."
sleep 10

echo ""
echo "📊 容器状态:"
$DOCKER_COMPOSE -f docker-compose.test.yml ps

echo ""
echo "✅ 健康检查:"
$DOCKER_COMPOSE -f docker-compose.test.yml ps | grep healthy || true

echo ""
echo "🎉 所有数据库服务已启动!"
echo ""
echo "连接信息:"
echo "  PostgreSQL: postgresql://test:test123@localhost:5433/stock_test"
echo "  ClickHouse: clickhouse://test:test123@localhost:9000/stock_test"
echo "  Redis: redis://localhost:6379"
echo ""
echo "查看日志: docker-compose -f docker-compose.test.yml logs -f"
echo "停止服务: docker-compose -f docker-compose.test.yml down"
echo "停止并删除数据: docker-compose -f docker-compose.test.yml down -v"
