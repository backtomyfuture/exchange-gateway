# Exchange Gateway 开源实施计划

**项目**: exchange-gateway  
**目标**: 将项目改造成符合业界最佳实践的开源项目  
**创建日期**: 2026-02-15

---

## 实施阶段总览

| 阶段 | 任务 | 状态 |
|------|------|------|
| Phase 1 | 代码清理与敏感信息移除 | 待执行 |
| Phase 2 | 许可证与版权声明 | 待执行 |
| Phase 3 | GitHub Actions CI/CD 配置 | 待执行 |
| Phase 4 | 文档体系重构 | 待执行 |
| Phase 5 | 项目配置与 README 重写 | 待执行 |
| Phase 6 | GitHub 仓库发布 | 待执行 |

---

## Phase 1: 代码清理与敏感信息移除

### 1.1 移除调试/测试脚本

| 文件 | 操作 |
|------|------|
| `check_folders.py` | 删除 |
| `check_subscription.py` | 删除 |
| `debug_menu_component.py` | 删除 |
| `debug_menu_tree.py` | 删除 |
| `dump_user_menu.py` | 删除 |
| `app/dump_user_menu.py` | 删除 |
| `app/fix_menu_icon.py` | 删除 |
| `scripts/test_prod_api.py` | 删除 |
| `scripts/test_verify_emails.py` | 删除 |
| `scripts/fix_menus_and_apis.py` | 删除 |

### 1.2 清理测试产物

| 文件 | 操作 |
|------|------|
| `test_output.txt` | 删除 |
| `build_log.txt` | 删除 |
| `recovered_editor.vue` | 删除 |
| `.pytest_cache/` | 删除 |

### 1.3 清理归档文件

| 文件 | 操作 |
|------|------|
| `scripts/archive/` | 评估后删除或保留 |
| `docs/plans/2026-02-15-remove-feishu-design.md` | 评估 |

### 1.4 敏感文件检查

- [ ] 确认 `.env` 已在 `.gitignore` 中
- [ ] 确认 `.secrets/` 已在 `.gitignore` 中
- [ ] 确认 `ssl/*.key` 已在 `.gitignore` 中
- [ ] 检查代码中无硬编码凭证

### 1.5 创建/更新 .env.example

创建包含所有必需配置项的示例文件，不含敏感值。

---

## Phase 2: 许可证与版权声明

### 2.1 更新 LICENSE 文件

将现有 LICENSE 内容替换为 Apache 2.0 许可证全文。

### 2.2 添加版权声明

在关键文件头部添加 Apache 2.0 版权声明：

```python
# Copyright 2024-2026 exchange-gateway
# Licensed under the Apache License, Version 2.0
```

### 2.3 保留原项目引用

在 LICENSE 或 README 中注明：
- 基于 `vue-fastapi-admin` (MIT) 二次开发
- 保留原项目版权声明

---

## Phase 3: GitHub Actions CI/CD 配置

### 3.1 创建目录结构

```
.github/
└── workflows/
    ├── test.yml
    ├── lint.yml
    └── release.yml
```

### 3.2 test.yml

- Python 3.11 环境
- 安装依赖
- 运行 pytest
- 覆盖率报告 (可选)

### 3.3 lint.yml

- Ruff 代码检查
- Black 格式检查 (可选)
- MyPy 类型检查 (可选)

### 3.4 release.yml (可选)

- 自动发布 PyPI
- Docker 镜像构建

---

## Phase 4: 文档体系重构

### 4.1 重写 README.md

- 项目名称改为 exchange-gateway
- 添加 Badge (License, Python version, Docker)
- 精简特性描述
- 优化快速开始代码块
- 添加目录结构说明

### 4.2 创建文档目录

```
docs/
├── getting-started.md      # 入门指南
├── deployment.md          # 部署指南
├── webhook.md             # Webhook 使用指南
├── api.md                 # API 参考 (可选：自动生成)
├── configuration.md       # 配置项详解
└── security.md            # 安全指南
```

### 4.3 创建 CHANGELOG.md

初始化版本记录，格式参照 Keep a Changelog。

---

## Phase 5: 项目配置与 README 重写

### 5.1 更新 pyproject.toml

- 项目名称: `exchange-gateway`
- 作者信息
- 描述信息
- Python 版本要求: `>=3.11`

### 5.2 更新 requirements.txt

- 固定所有依赖版本
- 移除不必要的依赖
- 添加版本说明注释

### 5.3 更新 docker-compose 文件

- 调整服务名称
- 添加注释说明
- 优化配置

### 5.4 更新 .gitignore

确保覆盖：
- Python 缓存
- Node_modules
- 环境文件
- 敏感文件

---

## Phase 6: GitHub 仓库发布

### 6.1 本地准备

- [ ] 所有代码变更已提交
- [ ] 分支已推送到远程
- [ ] 创建 GitHub 仓库

### 6.2 GitHub 配置

- [ ] 设置仓库 Description
- [ ] 添加 Topics: `exchange`, `ews`, `fastapi`, `email`, `webhook`, `python`
- [ ] 开启 Issues
- [ ] 开启 Discussions (可选)
- [ ] 添加 Issue Templates (Bug, Feature Request)

### 6.3 首次发布

- [ ] 创建首个 Release (v0.1.0)
- [ ] 编写 Release Notes

---

## 执行顺序建议

```
Phase 1 (代码清理)
    ↓
Phase 2 (许可证)
    ↓
Phase 3 (CI/CD)
    ↓
Phase 4 (文档)
    ↓
Phase 5 (配置)
    ↓
Phase 6 (发布)
```

---

## 风险与注意事项

| 风险 | 缓解措施 |
|------|----------|
| 遗漏敏感信息 | 人工复核 + grep 搜索关键词 |
| 破坏现有功能 | 在清理前确保测试通过 |
| 许可证合规 | 保留原项目声明 |

---

**计划创建完成，等待审批后执行。**
