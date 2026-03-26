from auth_utils import hash_password
from database import SessionLocal, init_database
from models import AdminUser

print('正在初始化数据库...')
init_database()
print('数据库表结构创建完成。')

db = SessionLocal()

try:
    admin_count = db.query(AdminUser).count()
    if admin_count == 0:
        default_password = 'heigo85'
        new_admin = AdminUser(username='admin', password_hash=hash_password(default_password))
        db.add(new_admin)
        db.commit()
        print('已创建默认管理员账户 - 用户名: admin, 密码: heigo85')
except Exception as exc:
    db.rollback()
    print(f'初始化管理员时出错: {exc}')
finally:
    db.close()

print('初始化完成。')
