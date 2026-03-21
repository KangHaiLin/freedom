#!/bin/bash
#
# 停止项目所有数据库服务
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "============================================"
echo "  停止项目数据库服务"
echo "============================================"
echo ""

# 询问是否保留数据卷
read -p "是否删除数据卷 (这会清空所有数据)? [y/N] " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "🛑 正在停止服务并删除数据卷..."
    if command -v docker-compose &> /dev/null; then
        docker-compose -f docker-compose.test.yml down -v
    else
        docker compose -f docker-compose.test.yml down -v
    fi
    echo "✅ 服务已停止，所有数据已删除"
else
    echo "🛑 正在停止服务（保留数据）..."
    if command -v docker-compose &> /dev/null; then
        docker-compose -f docker-compose.test.yml down
    else
        docker compose -f docker-compose.test.yml down
    fi
    echo "✅ 服务已停止，数据保留在docker volumes中"
fi
