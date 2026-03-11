FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码（包括数据库文件）
COPY . .

# 创建数据目录
RUN mkdir -p /app/data

# 暴露端口
EXPOSE 8080

# 启动命令：先初始化数据，再启动应用
CMD ["sh", "-c", "python init_data.py && uvicorn main1:app --host 0.0.0.0 --port 8080"]
