# A股量化交易系统 - 运维手册

本文档提供系统日常运维、监控告警、故障排查、备份恢复等操作指南。

## 目录

- [1. 日常运维操作](#1-日常运维操作)
  - [1.1 服务启停](#11-服务启停)
  - [1.2 查看日志](#12-查看日志)
  - [1.3 版本升级](#13-版本升级)
  - [1.4 回滚到历史版本](#14-回滚到历史版本)
- [2. 监控与告警](#2-监控与告警)
  - [2.1 系统监控指标](#21-系统监控指标)
  - [2.2 业务监控指标](#22-业务监控指标)
  - [2.3 告警配置](#23-告警配置)
  - [2.4 告警处理](#24-告警处理)
- [3. 数据管理](#3-数据管理)
  - [3.1 数据备份](#31-数据备份)
  - [3.2 数据恢复](#32-数据恢复)
  - [3.3 数据清理](#33-数据清理)
- [4. 性能优化](#4-性能优化)
  - [4.1 数据库优化](#41-数据库优化)
  - [4.2 应用优化](#42-应用优化)
- [5. 常见故障排查](#5-常见故障排查)
  - [5.1 服务启动失败](#51-服务启动失败)
  - [5.2 API 响应慢](#52-api-响应慢)
  - [5.3 数据库连接失败](#53-数据库连接失败)
  - [5.4 数据质量问题](#54-数据质量问题)
  - [5.5 内存占用过高](#55-内存占用过高)
- [6. 安全运维](#6-安全运维)
  - [6.1 日常安全检查](#61-日常安全检查)
  - [6.2 密码管理](#62-密码管理)
  - [6.3 备份验证](#63-备份验证)

---

## 1. 日常运维操作

### 1.1 服务启停

**systemd 方式（推荐生产环境）：**

```bash
# 启动服务
sudo systemctl start quant-trading

# 停止服务
sudo systemctl stop quant-trading

# 重启服务
sudo systemctl restart quant-trading

# 查看服务状态
sudo systemctl status quant-trading

# 查看服务是否开机自启
sudo systemctl is-enabled quant-trading

# 启用开机自启
sudo systemctl enable quant-trading

# 禁用开机自启
sudo systemctl disable quant-trading
```

**gunicorn 直接启动方式：**

```bash
# 启动（后台运行）
cd /path/to/stock
source venv/bin/activate
gunicorn src.user_interface.backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --daemon \
    --pid /var/run/quant-trading.pid

# 停止
kill $(cat /var/run/quant-trading.pid)
```

**开发环境（uvicorn）：**

```bash
# 启动（开发模式，自动重载）
cd /path/to/stock
source venv/bin/activate
uvicorn src.user_interface.backend.main:app --host 0.0.0.0 --port 8000 --reload

# 停止: Ctrl+C
```

### 1.2 查看日志

**systemd 日志：**

```bash
# 实时查看最新日志
journalctl -u quant-trading -f

# 查看最近100行
journalctl -u quant-trading -n 100

# 查看今天的日志
journalctl -u quant-trading --since today

# 查看错误级别日志
journalctl -u quant-trading -p err

# 清理旧日志（如果日志太大）
sudo journalctl --vacuum-size=100M
```

**应用日志文件：**

```bash
# 实时查看应用日志
tail -f /path/to/stock/logs/app.log

# 查看错误日志
tail -f /path/to/stock/logs/error.log

# 统计今日错误数量
grep "ERROR" /path/to/stock/logs/app.log | grep $(date +%Y-%m-%d) | wc -l
```

**数据库日志：**

```bash
# PostgreSQL 日志（Ubuntu/Debian）
sudo tail -f /var/log/postgresql/postgresql-*.log

# ClickHouse 日志
sudo tail -f /var/log/clickhouse-server/clickhouse-server.log

# Redis 日志
sudo tail -f /var/log/redis/redis-server.log
```

### 1.3 版本升级

遵循灰度升级流程，建议在低峰时段执行：

```bash
# 1. 拉取最新代码
cd /path/to/stock
git pull origin master

# 2. 检查变更（特别注意数据库变更）
git diff previous-tag..HEAD

# 3. 安装/更新依赖
source venv/bin/activate
pip install -r requirements.txt

# 4. 执行数据库迁移（如果有）
# psql -f scripts/migrations/xxx.sql

# 5. 重启服务
sudo systemctl restart quant-trading

# 6. 检查服务状态
sleep 10
sudo systemctl status quant-trading
curl http://localhost:8000/api/system/health
```

如果使用 Kubernetes：

```bash
# 更新镜像
kubectl set image deployment/quant-trading quant-trading=your-image:new-tag

# 查看滚动更新状态
kubectl rollout status deployment/quant-trading

# 确认升级完成
kubectl get pods
```

### 1.4 回滚到历史版本

如果升级后发现问题，立即回滚：

```bash
# 1. 查看版本历史
cd /path/to/stock
git log --oneline -10

# 2. 切换回上一个版本
git reset --hard HEAD^

# 或者回滚到指定 commit
git reset --hard <commit-hash>

# 3. 重启服务
sudo systemctl restart quant-trading

# 4. 验证服务正常
sleep 10
curl http://localhost:8000/api/system/health
```

---

## 2. 监控与告警

### 2.1 系统监控指标

**服务器基础监控：**

| 指标 | 正常范围 | 告警阈值 | 处理建议 |
|------|----------|----------|----------|
| CPU 使用率 | < 70% | > 85% 持续 5分钟 | 检查是否有异常进程，考虑扩容 |
| 内存使用率 | < 70% | > 85% 持续 5分钟 | 检查内存泄漏，调整应用配置 |
| 磁盘使用率 | < 70% | > 85% | 及时清理日志和旧数据 |
| 磁盘 IOPS | < 80% 峰值 | > 90% 持续 | 考虑升级更快存储 |
| 网络带宽 | < 70% | > 85% | 考虑升级带宽 |
| 负载均值 | < CPU 核心数 | > CPU 核心数 * 2 | 检查进程状态 |

### 2.2 业务监控指标

**数据质量监控（内置）：**
- 完整性：数据完整度 > 95%
- 准确性：数据准确率 > 99%
- 时效性：数据延迟 < 5分钟
- 一致性：数据一致性 > 99%

可以通过 API 获取：
```bash
# 最新数据质量
GET /api/monitor/data-quality/latest

# 历史趋势
GET /api/monitor/data-quality/history?days=30
```

**数据采集监控：**
- 每日行情数据采集成功率 > 99%
- 实时行情更新频率符合预期
- 无连续数据采集失败

**交易监控：**
- 订单发送成功率 > 99%
- 订单成交延迟 < 3秒
- 每日成交数量与预期相符

### 2.3 告警配置

系统支持多种告警渠道，在 `.env` 中配置：

```ini
# 企业微信告警（推荐）
WECHAT_WEBHOOK=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 邮件告警
EMAIL_SMTP_SERVER=smtp.qq.com
EMAIL_SMTP_PORT=587
EMAIL_USER=alerts@example.com
EMAIL_PASSWORD=your-app-password

# 短信告警（需要第三方短信服务）
SMS_API_KEY=your-api-key
```

**告警级别定义：**

| 级别 | 条件 | 处理时限 | 告警渠道 |
|------|------|----------|----------|
| P0 紧急 | 系统不可用，服务完全中断 | 15分钟 | 电话+短信+企业微信 |
| P1 重要 | 部分功能不可用，影响部分业务 | 1小时 | 短信+企业微信+邮件 |
| P2 一般 | 非核心功能异常，不影响主流程 | 4小时 | 企业微信+邮件 |
| P3 提示 | 系统存在潜在风险，需要关注 | 24小时 | 邮件 |

### 2.4 告警处理流程

1. **收到告警** → 确认告警级别
2. **登录服务器** → 查看日志，定位问题
3. **尝试恢复** → 优先恢复服务可用
4. **根因分析** → 找到问题根本原因
5. **修复问题** → 发布修复版本
6. **记录复盘** → 更新故障文档，避免重复发生

---

## 3. 数据管理

### 3.1 数据备份

**PostgreSQL 每日全量备份（推荐）：**

```bash
#!/bin/bash
# backup-postgres.sh
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backup/postgres
mkdir -p $BACKUP_DIR

# 全量备份
pg_dump -h $POSTGRES_HOST -p $POSTGRES_PORT -U $POSTGRES_USER $POSTGRES_DB \
    | gzip > $BACKUP_DIR/quant-$DATE.sql.gz

# 删除30天前的备份
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

# 验证备份文件大小
FILE_SIZE=$(stat -c%s $BACKUP_DIR/quant-$DATE.sql.gz)
if [ $FILE_SIZE -lt 1024 ]; then
    echo "Backup file too small, possible failure" | mail -s "PostgreSQL backup failed" admin@example.com
fi
```

添加到 cron 每日凌晨执行：

```
0 2 * * * /path/to/backup-postgres.sh >> /var/log/backup-postgres.log 2>&1
```

**ClickHouse 备份：**

ClickHouse 默认支持多副本，额外备份推荐：

```bash
#!/bin/bash
# backup-clickhouse.sh
DATE=$(date +%Y%m%d)
BACKUP_DIR=/backup/clickhouse
mkdir -p $BACKUP_DIR

# 使用 clickhouse-client 导出主要表
clickhouse-client --query "BACKUP TABLE quant.market_minute_quote TO 'file://$BACKUP_DIR/quant-market-minute-quote-$DATE.bak'"
clickhouse-client --query "BACKUP TABLE quant.market_daily_quote TO 'file://$BACKUP_DIR/quant-market-daily-quote-$DATE.bak'"

find $BACKUP_DIR -name "*.bak" -mtime +30 -delete
```

**配置文件备份：**

```bash
# 备份配置文件（每次部署前备份）
tar -zcf /backup/configs/config-$(date +%Y%m%d%H%M).tar.gz \
    /path/to/stock/.env \
    /path/to/stock/config/
```

### 3.2 数据恢复

**PostgreSQL 恢复：**

```bash
# 解压备份
gunzip < /backup/postgres/quant-YYYYMMDD.sql.gz | psql -h $HOST -p $PORT -U $USER $DB

# 如果需要先清空数据库
psql -h $HOST -p $PORT -U $USER $DB -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
gunzip < /backup/postgres/quant-YYYYMMDD.sql.gz | psql -h $HOST -p $PORT -U $USER $DB
```

**ClickHouse 恢复：**

```bash
clickhouse-client --query "RESTORE TABLE quant.market_minute_quote FROM 'file:///backup/clickhouse/quant-market-minute-quote-YYYYMMDD.bak'"
```

### 3.3 数据清理

**清理旧日志：**

```bash
# 清理 30 天前的日志
find /path/to/stock/logs -name "*.log" -mtime +30 -delete

# 清理 journalctl 日志
sudo journalctl --vacuum-size=100M
```

**清理 ClickHouse 旧数据（按时间分区）：**

```sql
-- 删除一年前的历史数据（根据实际需求调整）
ALTER TABLE quant.market_minute_quote DROP PARTITION 'yyyy-MM';
```

---

## 4. 性能优化

### 4.1 数据库优化

**PostgreSQL 优化（修改 `postgresql.conf`）：**

```ini
# 根据内存调整，推荐：内存 * 0.25
shared_buffers = 4GB

# 推荐：内存 * 0.5
effective_cache_size = 8GB

# 维护工作内存
maintenance_work_mem = 512MB

# 写入优化
wal_buffers = 16MB
checkpoint_completion_target = 0.9
```

**ClickHouse 优化（修改 `config.xml`）：**

```xml
<!-- 根据CPU核心数调整 -->
<max_threads>8</max_threads>

<!-- 内存限制 -->
<max_memory_usage>32GB</max_memory_usage>
<max_bytes_before_external_group_by>16GB</max_bytes_before_external_group_by>
```

### 4.2 应用优化

**Gunicorn 配置建议：**

- `workers` 数量：CPU 核心数 * 2 + 1
- 对于 CPU 密集型计算（回测）：workers = CPU 核心数
- 对于 I/O 密集型：workers = CPU 核心数 * 2

**启动参数示例（8核服务器）：**

```bash
gunicorn src.user_interface.backend.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --keep-alive 60
```

---

## 5. 常见故障排查

### 5.1 服务启动失败

**症状：** `systemctl start` 后服务立即退出

**排查步骤：**

```bash
# 1. 查看错误日志
journalctl -u quant-trading -n 50 --reverse

# 2. 检查配置文件是否存在
ls -la /path/to/stock/.env

# 3. 检查端口是否被占用
sudo lsof -i :8000
# 如果被占用，可以：
kill <pid>

# 4. 手动运行看错误
cd /path/to/stock
source venv/bin/activate
python -c "import src.user_interface.backend.main"
# 或者直接启动
gunicorn src.user_interface.backend.main:app --bind 0.0.0.0:8000

# 5. 检查磁盘空间
df -h
# 如果磁盘满了，清理日志
```

**常见原因：**
- 配置文件 `.env` 不存在 → 创建配置文件
- 依赖缺失 → 重新执行 `pip install -r requirements.txt`
- 端口被占用 → 停止占用端口的进程或修改端口
- 磁盘满了 → 清理日志/旧备份

### 5.2 API 响应慢

**症状：** API 响应时间超过 1秒

**排查步骤：**

```bash
# 1. 检查系统负载
top
# 查看 CPU、内存使用情况

# 2. 检查数据库慢查询
# PostgreSQL 查看慢查询
sudo -u postgres psql -c "SELECT query, calls, mean_time FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;"

# 3. 检查 ClickHouse 查询性能
clickhouse-client -q "SELECT query, elapsed FROM system.query_log ORDER BY elapsed DESC LIMIT 10;"

# 4. 检查连接数
# PostgreSQL
psql -c "SELECT count(*) FROM pg_stat_activity;"
```

**常见优化：**
- 添加缺失的数据库索引
- 优化慢查询语句
- 增加 Redis 缓存使用
- 考虑读写分离

### 5.3 数据库连接失败

**症状：** 应用日志出现 `could not connect to server`

**排查步骤：**

```bash
# 1. 检查数据库服务是否运行
sudo systemctl status postgresql
sudo systemctl status clickhouse-server
sudo systemctl status redis

# 2. 检查端口是否监听
netstat -tlnp | grep 5432
netstat -tlnp | grep 9000
netstat -tlnp | grep 6379

# 3. 测试连接
psql -h $host -p $port -U $user
clickhouse-client --host $host --port $port --user $user
```

**常见原因：**
- 数据库服务未启动 → `systemctl start`
- 防火墙阻挡 → 开放端口
- 配置错误（密码/端口不对） → 检查 `.env` 配置
- IP 地址白限制 → 检查数据库访问控制

### 5.4 数据质量问题

**症状：** 数据质量监控告警，完整性/准确性得分低于阈值

**排查步骤：**

```bash
# 1. 查看详细质量报告
curl http://localhost:8000/api/monitor/data-quality/latest

# 2. 检查数据源状态
# - 确认数据源API是否可用
# - 确认API Key是否过期
# - 确认当日是否交易日

# 3. 检查采集任务日志
grep "collector" /path/to/stock/logs/app.log | tail -20
```

**处理：**
- 如果数据源故障 → 等待数据源恢复，人工触发重采集
- 如果部分数据缺失 → 触发增量重采集
- 如果持续采集失败 → 检查网络连接和API权限

### 5.5 内存占用过高

**症状：** 内存使用率超过 90%，系统开始交换

**排查：**

```bash
# 查看进程内存排序
top -o %MEM

# 或者使用 ps
ps aux --sort=-%mem | head -10

# 检查 Python 内存
sudo apt install python3-memprof
# 重启应用并用 memprof 分析
```

**处理：**
- 重启服务释放内存：`sudo systemctl restart quant-trading`
- 如果内存持续增长，可能存在内存泄漏 → 需要开发定位修复
- 增加交换空间：

```bash
# 创建 4G 交换文件
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

## 6. 安全运维

### 6.1 日常安全检查

**每日检查：**
- 查看告警邮件/企业微信，确认无P0/P1告警
- 检查系统负载、磁盘使用

**每周检查：**
- 检查系统安全更新，及时安装补丁
- 检查访问日志，确认无异常访问
- 验证备份完整性

**每月检查：**
- 轮换数据库密码和API Key
- 检查防火墙规则，清理过期规则
- 进行灾难恢复演练（每季度一次）

### 6.2 密码管理

- 数据库密码长度至少 16 位，包含大小写、数字、符号
- API Key 不要提交到代码仓库
- 定期（每三个月）轮换一次密码
- 不同系统使用不同密码，推荐使用密码管理器

### 6.3 备份验证

- **每周**检查备份文件是否生成成功
- **每月**随机选择一个备份进行恢复测试
- 确认备份文件可以正常解压恢复
- 记录备份验证结果

---

## 联系支持

如果遇到本文档未涵盖的问题，请联系开发团队处理。

---

**文档版本：** v1.0 (2025-03-16)
**最后更新：** 2025-03-16
