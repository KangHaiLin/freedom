# A股量化交易系统 - 部署指南

本文档提供A股量化交易系统从环境准备到完整部署的详细步骤说明。

## 目录

- [1. 系统要求](#1-系统要求)
- [2. 环境准备](#2-环境准备)
- [3. 获取代码](#3-获取代码)
- [4. 配置修改](#4-配置修改)
- [5. 数据库初始化](#5-数据库初始化)
- [6. 启动服务](#6-启动服务)
- [7. 验证部署](#7-验证部署)
- [8. Docker Compose 快速部署（开发测试环境）](#8-docker-compose-快速部署开发测试环境)

---

## 1. 系统要求

### 1.1 硬件要求（开发测试环境）

| 组件 | 最低配置 | 推荐配置 |
|------|----------|----------|
| CPU | 4核 | 8核+ |
| 内存 | 16GB | 32GB+ |
| 磁盘 | 500GB SSD | 1TB SSD+ |
| 网络 | 1Gbps | 10Gbps |

### 1.2 软件要求

| 软件 | 最低版本 | 推荐版本 |
|------|----------|----------|
| Python | 3.8 | 3.10+ |
| PostgreSQL | 12 | 14+ |
| ClickHouse | 22.3 | 23.8+ |
| Redis | 6.0 | 7.0+ |
| Docker | 20.10 | 24.0+ |
| Docker Compose | v2 | v2+ |
| Git | 2.0 | 2.30+ |

---

## 2. 环境准备

### 2.1 安装系统依赖（Ubuntu/Debian）

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装基础工具
sudo apt install -y git vim wget curl build-essential \
    libssl-dev zlib1g-dev libbz2-dev libreadline-dev \
    libsqlite3-dev llvm libncurses5-dev libncursesw5-dev \
    xz-utils tk-dev libffi-dev liblzma-dev python3-openssl
```

### 2.2 安装 Python

推荐使用 pyenv 管理 Python 版本：

```bash
# 安装 pyenv
curl https://pyenv.run | bash

# 添加到 bashrc
echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc
echo 'command -v pyenv >/dev/null || export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc
echo 'eval "$(pyenv init -)"' >> ~/.bashrc
source ~/.bashrc

# 安装 Python 3.10
pyenv install 3.10.12
pyenv global 3.10.12

# 验证安装
python --version
# Python 3.10.12
```

### 2.3 安装数据库（裸机部署）

#### PostgreSQL

```bash
# 安装 PostgreSQL 14
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt update
sudo apt install -y postgresql-14 postgresql-contrib

# 启动服务
sudo systemctl enable postgresql
sudo systemctl start postgresql

# 创建数据库和用户
sudo -u postgres psql
```

```sql
-- 在 psql 中执行
CREATE DATABASE quant;
CREATE USER quant WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE quant TO quant;
ALTER DATABASE quant OWNER TO quant;
\q
```

#### ClickHouse

```bash
# 添加 ClickHouse 仓库
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv 8910F0FDBE804BD8280F404D1F97B525436FEF
echo "deb http://repo.clickhouse.com/deb/stable/ main/" | sudo tee /etc/apt/sources.list.d/clickhouse.list

# 安装
sudo apt update
sudo apt install -y clickhouse-server clickhouse-client

# 启动服务
sudo systemctl enable clickhouse-server
sudo systemctl start clickhouse-server

# 创建数据库
clickhouse-client -q "CREATE DATABASE IF NOT EXISTS quant;"
```

#### Redis

```bash
sudo apt install -y redis-server
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

---

## 3. 获取代码

```bash
# 克隆代码仓库
git clone <your-repo-url>
cd stock

# 切换到稳定分支
git checkout master
```

## 4. 配置修改

### 4.1 复制环境配置模板

```bash
cp .env.example .env
```

### 4.2 编辑配置文件

```bash
vim .env
```

根据实际环境修改以下配置：

```ini
# 服务配置
SERVICE_NAME=quant-trading-system
ENV=production
DEBUG=false
PORT=8000
HOST=0.0.0.0
SECRET_KEY=<your-strong-secret-key>  # 必须修改为强密钥

# PostgreSQL配置
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=quant
POSTGRES_PASSWORD=<your-password>
POSTGRES_DB=quant

# ClickHouse配置
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=<your-clickhouse-password>
CLICKHOUSE_DB=quant

# Redis配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=<your-redis-password>
REDIS_DB=0

# 数据源API Key - 必须配置至少一个
TUSHARE_API_KEY=your-tushare-api-key
WIND_API_KEY=your-wind-api-key
JOINQUANT_API_KEY=your-joinquant-api-key

# 告警配置
WECHAT_WEBHOOK=your-wechat-work-webhook-url
EMAIL_SMTP_SERVER=smtp.example.com
EMAIL_SMTP_PORT=587
EMAIL_USER=your-alert-email@example.com
EMAIL_PASSWORD=your-email-password-or-app-password
```

### 4.3 安装 Python 依赖

```bash
# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

## 5. 数据库初始化

### 5.1 初始化 PostgreSQL 表结构

```bash
psql -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER -d $POSTGRES_DB \
    -f scripts/init_postgres.sql
```

### 5.2 初始化 ClickHouse 表结构

```bash
clickhouse-client --host $CLICKHOUSE_HOST --port $CLICKHOUSE_PORT \
    --user $CLICKHOUSE_USER --password $CLICKHOUSE_PASSWORD \
    --multiquery < scripts/init_clickhouse.sql
```

## 6. 启动服务

### 6.1 使用 Gunicorn（生产环境推荐）

```bash
# 安装 gunicorn
pip install gunicorn uvicorn

# 启动服务（后台运行）
gunicorn src.user_interface.backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --daemon
```

### 6.2 使用 systemd 管理服务（推荐生产环境）

创建 service 文件：

```bash
sudo vim /etc/systemd/system/quant-trading.service
```

内容：

```ini
[Unit]
Description=Quantitative Trading System
After=network.target postgresql.service clickhouse-server.service redis-server.service

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/path/to/stock
Environment="PATH=/path/to/stock/venv/bin"
ExecStart=/path/to/stock/venv/bin/gunicorn \
    src.user_interface.backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120

Restart=always
RestartSec=10
StandardOutput=journal+console
StandardError=journal+console

[Install]
WantedBy=multi-user.target
```

启用并启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable quant-trading
sudo systemctl start quant-trading

# 查看状态
sudo systemctl status quant-trading
```

### 6.3 配置 Nginx 反向代理（推荐）

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    access_log /var/log/nginx/quant-access.log;
    error_log /var/log/nginx/quant-error.log;
}
```

如果需要 HTTPS，使用 Let's Encrypt 获取证书：

```bash
sudo certbot --nginx -d your-domain.com
```

## 7. 验证部署

### 7.1 检查服务健康

```bash
# 检查 API 健康状态
curl http://localhost:8000/api/system/health

# 预期响应
# {"code":200,"message":"ok","data":{"status":"healthy","timestamp":"..."}}
```

### 7.2 检查数据质量监控API

```bash
# 获取最新数据质量
curl http://localhost:8000/api/monitor/data-quality/latest

# 获取历史趋势（最近7天）
curl "http://localhost:8000/api/monitor/data-quality/history?days=7"
```

### 7.3 查看日志

```bash
# 如果使用 systemd
journalctl -u quant-trading -f

# 如果直接使用 gunicorn
tail -f logs/gunicorn.log
```

## 8. Docker Compose 快速部署（开发测试环境）

对于开发和测试环境，可以使用 Docker Compose 一键启动所有依赖服务：

### 8.1 启动依赖服务

```bash
# 启动 PostgreSQL、ClickHouse、Redis
docker-compose -f docker-compose.test.yml up -d

# 查看状态
docker-compose -f docker-compose.test.yml ps
```

### 8.2 等待初始化完成

查看初始化日志：

```bash
docker-compose -f docker-compose.test.yml logs -f postgres
docker-compose -f docker-compose.test.yml logs -f clickhouse
```

看到 `database system is ready to accept connections` 和 `Ready for connections` 表示初始化完成。

### 8.3 修改配置连接容器服务

修改 `.env` 文件：

```ini
POSTGRES_HOST=localhost
POSTGRES_PORT=5433  # 映射到宿主端口5433
POSTGRES_USER=test
POSTGRES_PASSWORD=test123
POSTGRES_DB=stock_test

CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=9000  # 映射到宿主端口9000
CLICKHOUSE_USER=test
CLICKHOUSE_PASSWORD=test123
CLICKHOUSE_DB=stock_test

REDIS_HOST=localhost
REDIS_PORT=6379  # 映射到宿主端口6379
```

### 8.4 初始化数据库

```bash
# PostgreSQL 初始化
docker exec -i stock-test-postgres psql -U test -d stock_test < scripts/init_postgres.sql

# ClickHouse 初始化
docker exec -i stock-test-clickhouse clickhouse-client < scripts/init_clickhouse.sql
```

### 8.5 启动应用

```bash
source venv/bin/activate
python -m uvicorn src.user_interface.backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### 8.6 停止服务

```bash
# 停止并保留数据
docker-compose -f docker-compose.test.yml stop

# 完全删除（数据会丢失）
docker-compose -f docker-compose.test.yml down -v
```

## 部署完成

恭喜！系统已成功部署。请参考 [运维手册](./operations-guide.md) 了解日常运维操作。
