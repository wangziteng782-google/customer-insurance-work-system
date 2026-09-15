"""重置测试用户密码为 123456（用于接口测试）"""
import sys
sys.path.insert(0, r'c:/wzt_WorkFile/project/customer-insurance-work-system/backend')
from cit_api.database import SessionLocal
from cit_api.model.model import User
import bcrypt

db = SessionLocal()
u = db.query(User).filter(User.username == 'wz').first()
if u:
    u.password = bcrypt.hashpw(b'123456', bcrypt.gensalt(10)).decode()
    db.commit()
    print(f'RESET OK: wz / 123456, user_id={u.id}, phone={u.phone}')
else:
    print('用户 wz 不存在，请检查数据库')
db.close()