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
ARG NGINX_ENV=prod

# 复制 nginx 配置文件（根据 NGINX_ENV 选择）
RUN if [ "$NGINX_ENV" = "dev" ]; then \
        echo "Using development nginx config (HTTP)" && \
        cp /deploy/nginx/nginx.dev.conf /etc/nginx/nginx.conf; \
    else \
        echo "Using production nginx config (HTTPS)" && \
        cp /deploy/nginx/nginx.conf /etc/nginx/nginx.conf; \
    fi

# 复制配置文件到镜像
COPY deploy/nginx/nginx.conf /deploy/nginx/nginx.conf
COPY deploy/nginx/nginx.dev.conf /deploy/nginx/nginx.dev.conf

# 仅在生产模式复制 SSL 证书
RUN if [ "$NGINX_ENV" = "prod" ]; then \
        mkdir -p /etc/nginx/ssl && \
        cp /ssl/exchange.crt /etc/nginx/ssl/exchange.crt && \
        cp /ssl/exchange.key /etc/nginx/ssl/exchange.key && \
        chmod 600 /etc/nginx/ssl/exchange.key && \
        chmod 644 /etc/nginx/ssl/exchange.crt; \
    fi

# 从构建阶段复制产物
COPY --from=build-stage /app/dist /usr/share/nginx/html
RUN chmod -R 755 /usr/share/nginx/html && \
    chown -R nginx:nginx /usr/share/nginx/html

# 健康检查（统一使用 HTTP）
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/nginx-health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
