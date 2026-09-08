"""初始化用户数据（默认密码 123456）"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

import bcrypt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from cit_api.model.model import Base, User

# ── 数据库连接（按需修改）──
DB_URL = "mysql+pymysql://root:1234@localhost:3306/insurance_work"
engine = create_engine(DB_URL)
SessionLocal = sessionmaker(bind=engine)

USERS = [
    {"username": "wj", "display_name": "温珺", "role": 2, "phone": "15530103723"},
    {"username": "wb", "display_name": "武彬", "role": 2, "phone": "13785101571"},
    {"username": "lxh", "display_name": "梁晓红", "role": 2, "phone": "18033727169"},
    {"username": "lhn", "display_name": "郎汉宁", "role": 2, "phone": "13785200383"},
    {"username": "lpx", "display_name": "李盼想", "role": 2, "phone": "19538139235"},
    {"username": "sxs", "display_name": "孙兴素", "role": 2, "phone": "13933037611"},
    {"username": "ncl", "display_name": "牛翠丽", "role": 2, "phone": "18032929703"},
    {"username": "hxl", "display_name": "韩晓林", "role": 2, "phone": "15532116055"},
    {"username": "csq", "display_name": "崔素庆", "role": 2, "phone": "13932160914"},
]


def init():
    db = SessionLocal()
    try:
        for u in USERS:
            if db.query(User).filter(User.username == u["username"]).first():
                print(f"用户 {u['username']} 已存在，跳过")
                continue
            u["password"] = bcrypt.hashpw("123456".encode(), bcrypt.gensalt(10)).decode()
            db.add(User(**u))
            print(f"创建用户: {u['username']}")
        db.commit()
        print("初始化完成")
    finally:
        db.close()


if __name__ == "__main__":
    init()
