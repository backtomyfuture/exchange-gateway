# Exchange Gateway - Docker 部署总结

## 部署信息

**部署时间**: 2026-02-18 13:12:00
**部署状态**: ✅ 成功
**环境**: 开发模式 (dev)

## 配置信息

```
EXCHANGE_SERVER=mail.hnair.com
EXCHANGE_DOMAIN=hnanet
EXCHANGE_EMAIL_SUFFIX=@tianjin-air.com
ENV=dev
```

## 运行容器

| 容器名称 | 镜像 | 状态 | 端口映射 |
|---------|------|------|---------|
| exchange-gateway-mysql | mysql:8.0 | ✅ Running (Healthy) | 13306:3306 |
| exchange-gateway-app | exchange-app:latest | ✅ Running | 18001:8000 |
| exchange-gateway-nginx | exchange-gateway-nginx | ✅ Running | 80:8080 |
| exchange-gateway-webhook-worker | exchange-app:latest | ✅ Running | 8000 (内部) |

## 访问信息

### 1. 管理后台
- **URL**: http://localhost
- **端口**: 80 (Nginx 反向代理)
- **说明**: 完整的 Vue3 管理仪表板，可以管理账户、API 密钥、邮件模板等

### 2. API 文档 (Swagger UI)
- **URL**: http://localhost/docs
- **说明**: FastAPI 自动生成的交互式 API 文档

### 3. 直接应用访问 (开发)
- **URL**: http://localhost:18001
- **端口**: 18001
- **说明**: 后端 FastAPI 服务直接访问

### 4. 健康检查
- **URL**: http://localhost:18001/api/v1/exchange/health
- **说明**: 检查应用健康状态

### 5. 数据库访问 (MySQL)
- **Host**: localhost
- **Port**: 13306
- **Username**: root
- **Password**: root123
- **Database**: exchange_gateway

## 重要信息

### 开发模式警告
⚠️ 当前运行在 **开发模式 (ENV=dev)**，这意味着：
- SECRET_KEY 和 EXCHANGE_ENCRYPTION_KEY 会自动生成（未显示警告）
- HTTP 协议（非 HTTPS）
- 安全策略较为宽松
- 仅用于开发和测试

### 对于生产环境
生产部署前，请修改 `.env` 文件：
```bash
# 生成密钥
SECRET_KEY=$(openssl rand -hex 32)
EXCHANGE_ENCRYPTION_KEY=$(python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())")

# 更新 .env
ENV=prod
SECRET_KEY=<上面生成的值>
EXCHANGE_ENCRYPTION_KEY=<上面生成的值>
```

然后重新启动：
```bash
docker compose down
docker compose up -d
```

## 常用命令

### 查看容器状态
```bash
docker compose ps
```

### 查看应用日志
```bash
docker compose logs app -f
```

### 重启服务
```bash
docker compose restart
```

### 停止容器
```bash
docker compose down
```

### 完全清理（包括数据）
```bash
docker compose down -v
```

## 默认凭证

首次登录管理后台时，请使用默认管理员账号：
- **用户名**: admin
- **密码**: admin123

⚠️ 建议首次登录后立即修改密码

## 文件位置

- **配置文件**: `.env`
- **数据目录**: `.docker-data/`
  - MySQL 数据: `.docker-data/mysql`
  - 应用日志: `.docker-data/logs`

## 故障排除

### 1. 容器启动失败
检查日志：
```bash
docker compose logs [service-name]
```

### 2. 数据库连接失败
确保 MySQL 容器正常运行：
```bash
docker compose logs mysql
```

### 3. 清理并重新部署
```bash
docker compose down -v  # 删除所有容器和数据
docker compose up -d    # 重新启动
```

## 下一步

1. 访问管理后台: http://localhost
2. 使用默认凭证登录 (admin/admin123)
3. 配置 Exchange 账户和 API 密钥
4. 查看 API 文档: http://localhost/docs
5. 测试 API 端点

## 相关文档

- [README.md](README.md) - 项目概述
- [docs/deployment.md](docs/deployment.md) - 详细部署指南
- [docs/api.md](docs/api.md) - API 参考文档
- [docs/configuration.md](docs/configuration.md) - 配置详解

---

祝您使用愉快！
