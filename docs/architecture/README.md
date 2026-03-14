# 架构设计文档总览

## 文档概述
本文档是A股量化交易软件系统的架构设计说明书，基于IEEE 1471标准和项目需求规格说明书(SRS)编制，是系统开发、测试、部署和运维的核心依据。

## 文档结构
```
docs/architecture/
├── README.md                     # 架构设计总览（本文档）
├── 1-overall-architecture.md     # 总体架构设计
├── 2-subsystem-design.md         # 子系统详细设计
├── 3-database-architecture.md    # 数据库架构设计
├── 4-interface-specification.md  # 接口规范设计
├── 5-deployment-architecture.md  # 部署架构设计
├── 6-security-architecture.md    # 安全架构设计
├── 7-tech-stack-selection.md     # 技术选型说明 (待补充)
└── 8-quality-attributes.md       # 质量属性设计 (待补充)
```

## 设计原则
1. **合规优先**：严格遵循A股市场监管要求，T+1、涨跌停限制等规则内置到系统核心
2. **性能导向**：满足回测速度≤180秒、写入性能≥10万条/秒的性能指标
3. **高可用**：核心系统99.99%可用性，数据持久化可靠性99.999%
4. **可扩展**：支持业务功能和数据规模的平滑扩展
5. **易维护**：模块化设计，清晰的接口定义，降低耦合度
6. **安全可靠**：多层次安全防护，交易数据和策略加密存储

## 架构决策
1. **混合数据库架构**：InfluxDB(实时数据) + ClickHouse(分析数据) + PostgreSQL(业务数据)
2. **微服务架构**：基于Docker+Kubernetes的容器化部署
3. **事件驱动**：Kafka消息队列实现系统解耦和异步处理
4. **分层架构**：表现层、API网关层、服务层、数据访问层、基础设施层
5. **迭代开发**：2周一个迭代，分阶段交付功能

## 版本信息
| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-03-20 | 架构组 | 初始版本 |

## 相关文档
- [SRS需求规格说明书](../srs/README.md)
- [技术可行性评估报告](../validation/technical-feasibility-assessment-report.md)
- [项目章程](../validation/project-charter.md)
