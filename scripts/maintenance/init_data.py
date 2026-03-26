"""
初始化数据脚本 - 将本地数据库复制到Volume
"""
import os
import shutil
import sys

# 源数据库文件（部署时包含的）
source_db = "/app/fm_league.db"

# 目标路径（Volume挂载点）
data_dir = "/app/data"
target_db = os.path.join(data_dir, "fm_league.db")

def init_database():
    """初始化数据库到Volume"""
    # 确保数据目录存在
    os.makedirs(data_dir, exist_ok=True)
    
    # 如果Volume中没有数据库，复制部署时包含的数据库
    if not os.path.exists(target_db):
        if os.path.exists(source_db):
            print(f"正在复制数据库到Volume: {source_db} -> {target_db}")
            shutil.copy2(source_db, target_db)
            print("数据库复制成功！")
        else:
            print(f"警告：源数据库不存在: {source_db}")
            print("将创建新的空数据库")
    else:
        print(f"Volume中已存在数据库: {target_db}")
        print("跳过复制，保留现有数据")

if __name__ == "__main__":
    init_database()
