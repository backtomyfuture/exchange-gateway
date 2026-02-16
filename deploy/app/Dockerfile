# FastAPI 应用镜像 (Multi-stage Build)
# 支持自定义镜像源，通过 --build-arg 传入
ARG PYTHON_IMAGE=python:3.11-slim-bullseye
ARG PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG APT_MIRROR=mirrors.ustc.edu.cn

# Stage 1: Builder
FROM ${PYTHON_IMAGE} as builder

ARG PIP_INDEX_URL
ARG APT_MIRROR

WORKDIR /build

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 安装构建依赖
RUN sed -i "s@http://.*.debian.org@https://${APT_MIRROR}@g" /etc/apt/sources.list && \
    sed -i "s@http://security.debian.org@https://${APT_MIRROR}/debian-security@g" /etc/apt/sources.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    libxml2-dev \
    libxslt-dev \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*

# 创建虚拟环境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i ${PIP_INDEX_URL}


# Stage 2: Runner
FROM ${PYTHON_IMAGE}

ARG APT_MIRROR

WORKDIR /opt/app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/app \
    TZ=Asia/Shanghai \
    PATH="/opt/venv/bin:$PATH"

# 安装运行时系统依赖 (去除构建工具，保留库文件)
RUN sed -i "s@http://.*.debian.org@https://${APT_MIRROR}@g" /etc/apt/sources.list && \
    sed -i "s@http://security.debian.org@https://${APT_MIRROR}/debian-security@g" /etc/apt/sources.list && \
    ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    libxml2 \
    libxslt1.1 \
    curl \
    netcat-openbsd \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 从 builder 阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 复制应用代码
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY deploy/app/entrypoint.sh .
RUN sed -i 's/\r$//' entrypoint.sh && chmod +x entrypoint.sh

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser

# 创建日志目录并设置权限
RUN mkdir -p /var/log/app && \
    chown -R appuser:appuser /opt/app /var/log/app

USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
