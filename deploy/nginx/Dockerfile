# Stage 1: Build frontend
FROM node:18-alpine AS build-stage

# 钉 pnpm 9：pnpm 10 默认忽略依赖 build scripts，会报 ERR_PNPM_IGNORED_BUILDS
RUN npm install -g pnpm@9.15.9

WORKDIR /app

# 先复制依赖定义文件
COPY web/package.json web/pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install --frozen-lockfile

# 复制源码并构建
COPY web/ .
RUN pnpm run build

# Stage 2: Serve with Nginx
FROM nginx:1.25-alpine

# 支持通过 build-arg 选择配置:
# railway: Railway edge 已终止 TLS，容器监听 $PORT
# dev: 使用 nginx.dev.conf (HTTP only, 8080)
# prod: 使用 nginx.conf (HTTPS, 自托管)
ARG NGINX_ENV=railway

# 先复制配置文件到镜像
COPY deploy/nginx/nginx.conf /deploy/nginx/nginx.conf
COPY deploy/nginx/nginx.dev.conf /deploy/nginx/nginx.dev.conf
COPY deploy/nginx/nginx.railway.conf /deploy/nginx/nginx.railway.conf

# 根据 NGINX_ENV 选择配置文件
RUN if [ "$NGINX_ENV" = "dev" ]; then \
        echo "Using development nginx config (HTTP)" && \
        cp /deploy/nginx/nginx.dev.conf /etc/nginx/nginx.template; \
    elif [ "$NGINX_ENV" = "railway" ]; then \
        echo "Using Railway nginx config (HTTP on \$PORT)" && \
        cp /deploy/nginx/nginx.railway.conf /etc/nginx/nginx.template; \
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
    CMD wget -q -O /dev/null "http://127.0.0.1:$${PORT:-8080}/nginx-health" || exit 1

EXPOSE 8080

# 在启动 Nginx 前使用 envsubst 替换环境变量。
# Railway 的私有 DNS 地址从 resolv.conf 动态读取，并由模板强制使用 IPv4。
CMD ["/bin/sh", "-c", "export BACKEND_HOST=${BACKEND_HOST:-app.railway.internal} && export BACKEND_PORT=${BACKEND_PORT:-8000} && export PORT=${PORT:-8080} && export RESOLVER=${RESOLVER:-$(awk '/^[[:space:]]*nameserver[[:space:]]/{print $2; exit}' /etc/resolv.conf)} && : \"${RESOLVER:=127.0.0.11}\" && case \"$RESOLVER\" in *:*:*) case \"$RESOLVER\" in \\[*\\]*) ;; *) RESOLVER=\"[$RESOLVER]\" ;; esac ;; esac && envsubst '$BACKEND_HOST $BACKEND_PORT $PORT $RESOLVER' < /etc/nginx/nginx.template > /etc/nginx/nginx.conf && exec nginx -g 'daemon off;'"]
