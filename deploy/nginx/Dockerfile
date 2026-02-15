# Stage 1: Build frontend
FROM node:18-alpine AS build-stage

# 安装 pnpm
RUN npm install -g pnpm

WORKDIR /app

# 先复制依赖定义文件
COPY web/package.json web/pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 复制源码并构建
COPY web/ .
RUN pnpm run build

# Stage 2: Serve with Nginx
FROM nginx:1.25-alpine

# 复制 nginx 配置
COPY deploy/nginx/nginx.conf /etc/nginx/nginx.conf

# 复制 SSL 证书
COPY ssl/exchange.crt /etc/nginx/ssl/exchange.crt
COPY ssl/exchange.key /etc/nginx/ssl/exchange.key
RUN chmod 600 /etc/nginx/ssl/exchange.key && \
    chmod 644 /etc/nginx/ssl/exchange.crt

# 从构建阶段复制产物
COPY --from=build-stage /app/dist /usr/share/nginx/html
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

# 健康检查（使用 HTTPS）
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --no-check-certificate -O /dev/null https://127.0.0.1/nginx-health || exit 1

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
