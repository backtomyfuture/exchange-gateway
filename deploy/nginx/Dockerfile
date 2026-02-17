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

# 支持通过 build-arg 选择配置: --build-arg NGINX_ENV=dev
# dev: 使用 nginx.dev.conf (HTTP only)
# prod: 使用 nginx.conf (HTTPS)
ARG NGINX_ENV=dev

# 先复制配置文件到镜像
COPY deploy/nginx/nginx.conf /deploy/nginx/nginx.conf
COPY deploy/nginx/nginx.dev.conf /deploy/nginx/nginx.dev.conf

# 根据 NGINX_ENV 选择配置文件
RUN if [ "$NGINX_ENV" = "dev" ]; then \
        echo "Using development nginx config (HTTP)" && \
        cp /deploy/nginx/nginx.dev.conf /etc/nginx/nginx.template; \
    else \
        echo "Using production nginx config (HTTPS)" && \
        cp /deploy/nginx/nginx.conf /etc/nginx/nginx.template; \
    fi

# 安装 gettext 以获取 envsubst，并清理缓存
RUN apk add --no-cache gettext

# 仅在生产模式且 SSL 证书存在时复制
# SSL certificates should be mounted at runtime via volumes or provided during build
# For now, create empty directory structure
RUN mkdir -p /etc/nginx/ssl

# 从构建阶段复制产物
COPY --from=build-stage /app/dist /usr/share/nginx/html
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

# 健康检查（统一使用 HTTP）
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:8080/nginx-health || exit 1

EXPOSE 8080

# 在启动 Nginx 前使用 envsubst 替换环境变量
# 如果没设置变量，设置默认值以防报错
CMD ["/bin/sh", "-c", "export BACKEND_HOST=${BACKEND_HOST:-app.railway.internal} && export BACKEND_PORT=${BACKEND_PORT:-8000} && envsubst '$BACKEND_HOST $BACKEND_PORT' < /etc/nginx/nginx.template > /etc/nginx/nginx.conf && exec nginx -g 'daemon off;'"]
