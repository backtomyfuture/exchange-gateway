# Exchange Gateway 开源改造设计方案

**项目名称**: exchange-gateway  
**目标**: 建立技术品牌  
**平台**: GitHub  
**许可证**: Apache 2.0  
**日期**: 2026-02-15

---

## 1. 项目定位与市场分析

### 1.1 项目定位

**一句话描述**: 基于 FastAPI + exchangelib 的企业级 Exchange/EWS 邮件网关，提供 RESTful API 和 Webhook 事件订阅能力。

**核心价值**:
- 简化 Exchange/EWS 集成，无需深入了解微软 EWS 协议
- 支持邮件发送、接收、模板管理、事件订阅（Webhook）
- 内置管理后台，降低运维成本

### 1.2 目标用户

| 用户群体 | 使用场景 |
|---------|---------|
| 开发团队 | 需集成企业邮箱能力的 SaaS/内部系统 |
| 运维工程师 | 统一管理企业邮件发送 |
| 系统集成商 | 为客户搭建邮件自动化流程 |

### 1.3 竞品分析

| 竞品 | 优点 | 不足 |
|-----|------|------|
| exchangelib (Python 库) | 功能完整 | 仅是 SDK，非完整服务 |
| EWS Managed API (C#) | 微软官方 | 仅支持 .NET |
| mailcow | 完整邮件服务器 | 过于重量级，非专注 EWS |
| **exchange-gateway** | 轻量、API 驱动、Webhook 支持 | 需自建服务 |

---

## 2. 开源策略设计

### 2.1 许可证架构

```
┌─────────────────────────────────────────┐
│           exchange-gateway               │
│            Apache 2.0                    │
├─────────────────────────────────────────┤
│  基于 vue-fastapi-admin (MIT) 二次开发   │
│  - 保留原项目版权声明                    │
│  - 添加本项目 Apache 2.0 许可证         │
└─────────────────────────────────────────┘
```

**许可证说明**:
- 主许可证: Apache 2.0
- 前端部分引用: vue-fastapi-admin (MIT)
- 兼容声明: 在 LICENSE 和 README 中注明

### 2.2 项目结构重命名

| 现有 | 开源后 |
|-----|-------|
| (无) | exchange-gateway |
| README.md | 保持 |
| CLAUDE.md | 移除或移至 .claude/ |

### 2.3 代码清理清单

| 类别 | 操作 |
|-----|------|
| **敏感信息** | 移除 .env、.secrets/、硬编码凭证 |
| **本地调试** | 移除 check_*.py、debug_*.py、dump_*.py |
| **测试产物** | 移除 test_output.txt、build_log.txt |
| **临时文件** | 移除 .pytest_cache/、recovered_editor.vue |
| **依赖锁定** | 更新 requirements.txt 使用固定版本 |

---

## 3. GitHub 项目配置

### 3.1 仓库设置

```
名称: exchange-gateway
描述: Enterprise-grade Exchange/EWS mail gateway with REST API and Webhook support
私有/公开: 公开 (Public)
```

### 3.2 README 结构 (新)

```markdown
# exchange-gateway

Enterprise-grade Exchange/EWS mail gateway built with FastAPI.

[Badges: License, CI, Python version, Docker]

## Features

- 📧 Send/Receive emails via REST API
- 🔗 Webhook event subscription (NewMail, Created, Modified, etc.)
- 📊 Admin dashboard (Vue3 + Naive UI)
- 🔒 Security: AES-256-GCM encryption, API Key auth
- 🐳 Docker deployment

## Quick Start

[docker-compose 快速启动]

## Documentation

- [API Reference](docs/api.md)
- [Deployment Guide](docs/deployment.md)
- [Webhook Guide](docs/webhook.md)

## Comparison

[与 exchangelib 直接使用对比]

## License

Apache 2.0 - see [LICENSE](LICENSE)
```

### 3.3 GitHub 最佳实践配置

| 项目 | 建议 |
|-----|------|
| **Description** | 一句话描述 + 关键字 |
| **Topics** | exchange, ews, fastapi, email, webhook, python |
| **Website** | 可选：文档链接 |
| **Sponsors** | 暂不需 |
| **Issues** | 开启，允许 bug report |
| **Discussions** | 开启，用于 Q&A |
| **Projects** | 可选：看板管理 |

---

## 4. 核心改造方案

### 4.1 依赖与环境

#### 4.1.1 Python 依赖整理

**原则**: 使用固定版本，确保可复现性

```txt
# 核心框架 (锁定版本)
fastapi==0.115.0
uvicorn[standard]==0.34.0
tortoise-orm==0.23.0
aerich==0.8.1

# Exchange 集成
exchangelib==5.6.0

# 安全
cryptography==44.0.0
pyjwt==2.10.1
passlib==1.7.4
argon2-cffi==23.1.0

# 工具
python-dotenv==1.0.1
pydantic==2.10.5
pydantic-settings==2.7.1

# 其他 (按需精简)
...
```

#### 4.1.2 前端依赖

检查 package.json，移除不必要的开发依赖。

#### 4.1.3 Docker 镜像优化

```dockerfile
# 多阶段构建
FROM python:3.11-slim AS builder
...

FROM python:3.11-slim
# 最小化运行时镜像
```

### 4.2 配置与凭证管理

#### 4.2.1 环境变量重构

```bash
# .env.example (开源版本)
EXCHANGE_SERVER=your-exchange-server.com
EXCHANGE_DOMAIN=your-domain
DATABASE_URL=mysql://user:pass@localhost:3306/exchange
REDIS_URL=redis://localhost:6379/0

# 生产必须配置
EXCHANGE_ENCRYPTION_KEY=  # 用户必须自己生成

# 可选配置
LOG_LEVEL=INFO
WEBHOOK_ALLOW_PRIVATE_URLS=false
DEV_MODE=false
```

#### 4.2.2 敏感文件处理

| 文件 | 处理方式 |
|-----|---------|
| .env | 已加入 .gitignore |
| .secrets/ | 移除或加入 .gitignore |
| ssl/*.key | 保持 .gitignore |
| build_log.txt | 移除 |

### 4.3 目录结构优化

```
exchange-gateway/
├── app/                    # FastAPI 应用
├── web/                    # Vue3 管理后台
├── tests/                  # 测试
├── docs/                   # 文档
│   ├── api.md
│   ├── deployment.md
│   ├── webhook.md
│   └── ...
├── docker/                 # Docker 配置
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── nginx.conf
├── scripts/                # 运维脚本
├── migrations/            # 数据库迁移
├── .github/                # GitHub Actions
│   └── workflows/
│       ├── test.yml
│       └── release.yml
├── LICENSE                 # Apache 2.0
├── README.md
├── pyproject.toml
├── requirements.txt
└── .env.example
```

### 4.4 CI/CD 配置

#### 4.4.1 GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Run tests
        run: |
          pip install -r requirements.txt
          pytest tests/ -v
```

```yaml
# .github/workflows/lint.yml
name: Lint
on: [push, pull_request]

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Ruff linter
        uses: astral-sh/ruff-action@v3
```

---

## 5. 文档体系设计

### 5.1 文档结构

| 文档 | 内容 | 优先级 |
|-----|------|-------|
| README.md | 项目介绍、快速开始、特性 | 必须 |
| docs/getting-started.md | 详细入门指南 | 必须 |
| docs/api.md | API 参考 (自动生成或手动) | 必须 |
| docs/deployment.md | 部署指南 (Docker/K8s) | 必须 |
| docs/webhook.md | Webhook 使用指南 | 必须 |
| docs/configuration.md | 配置项详解 | 中 |
| docs/security.md | 安全配置指南 | 中 |
| CHANGELOG.md | 版本变更记录 | 推荐 |

### 5.2 文档风格

- 使用 Markdown
- 代码块标注语言
- 命令行示例使用 `$` 前缀
- 配置项使用表格

---

## 6. 开源发布检查清单

### 6.1 代码层面

- [ ] 移除所有硬编码凭证、API Key、密码
- [ ] 清理调试脚本 (check_*.py, debug_*.py)
- [ ] 清理测试产物 (test_output.txt, build_log.txt)
- [ ] 更新 .gitignore 覆盖所有敏感文件
- [ ] 添加 .env.example
- [ ] 固定所有依赖版本

### 6.2 项目配置

- [ ] 更新 pyproject.toml (项目名称、作者)
- [ ] 更新 package.json (如需)
- [ ] 添加 LICENSE 文件 (Apache 2.0)
- [ ] 添加 .github/workflows/ (CI/CD)
- [ ] 添加 .github/ISSUE_TEMPLATE/ (Bug/Feature)

### 6.3 文档层面

- [ ] 重写 README.md (适配开源)
- [ ] 创建 docs/getting-started.md
- [ ] 创建 docs/deployment.md
- [ ] 创建 CHANGELOG.md

### 6.4 GitHub 层面

- [ ] 创建公开仓库
- [ ] 配置仓库 Description、Topics
- [ ] 开启 Issues、Discussions
- [ ] 添加 GitHub Actions secrets (如需)

---

## 7. 实施建议

### 7.1 分阶段实施

| 阶段 | 任务 | 预计工作量 |
|-----|------|----------|
| Phase 1 | 代码清理、环境隔离 | 1-2 小时 |
| Phase 2 | 许可证、版权声明 | 0.5 小时 |
| Phase 3 | GitHub Actions 配置 | 1 小时 |
| Phase 4 | 文档重写 | 2-3 小时 |
| Phase 5 | README/项目配置 | 1 小时 |
| Phase 6 | 发布与宣传 | 持续 |

### 7.2 关键风险

| 风险 | 缓解措施 |
|-----|---------|
| 遗漏敏感信息 | 使用 git-secrets 或 gitleaks 扫描 |
| 许可证合规 | 保留原项目声明，添加本项目许可 |
| 文档不完整 | 先完成核心文档再发布 |

---

## 8. 后续运营建议

### 8.1 吸引关注

- 在 Reddit、Twitter、V2EX 等平台分享
- 在掘金、CSDN 等国内平台发布中文文章
- 提交到 awesome-python、awesome-fastapi 等列表

### 8.2 社区建设

- 及时回复 Issues
- 定期发布新版本 (使用 GitHub Releases)
- 添加贡献指南 CONTRIBUTING.md

---

**设计完成，等待用户审批后执行。**
