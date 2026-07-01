FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080 \
    DATABASE_PATH=/app/data/fm_league.db \
    HEIGO_IMPORT_ROOT=/app/imports \
    HEIGO_BACKUP_ROOT=/app/data/backups

WORKDIR /app

COPY requirements.txt ./
RUN sed -i 's#http://deb.debian.org/debian#https://mirrors.tencent.com/debian#g; s#http://deb.debian.org/debian-security#https://mirrors.tencent.com/debian-security#g' /etc/apt/sources.list.d/debian.sources
RUN apt-get update \
    && apt-get install -y --no-install-recommends libcairo2 libffi-dev fontconfig fonts-noto-cjk \
    && rm -rf /var/lib/apt/lists/*
RUN pip install --default-timeout=300 --retries 10 -i https://pypi.tuna.tsinghua.edu.cn/simple --trusted-host pypi.tuna.tsinghua.edu.cn --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/data /app/imports /app/data/backups \
    && chmod +x /app/docker-entrypoint.sh

EXPOSE 8080

ENTRYPOINT ["/app/docker-entrypoint.sh"]
