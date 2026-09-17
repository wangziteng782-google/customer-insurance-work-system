from sqlalchemy import Column, BigInteger, String, Text, DateTime, func, JSON, Integer
from sqlalchemy.dialects.mysql import TINYINT
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class ChatMessage(Base):
    """聊天记录表"""
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    task_id = Column(String(32), nullable=False, index=True, comment="任务编号")
    content = Column(Text, nullable=False, comment="消息内容")
    file_paths = Column(JSON, nullable=True, comment="附件路径列表")
    creator = Column(String(50), nullable=True, comment="发送人")
    user_id = Column(BigInteger, nullable=True, comment="发送人ID")
    created_at = Column(DateTime, server_default=func.now(), comment="发送时间")


class InsuranceTask(Base):
    """任务主表"""
    __tablename__ = "insurance_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    task_id = Column(String(32), nullable=False, unique=True, comment="任务ID")
    status = Column(TINYINT, nullable=False, default=1, comment="1进行中/2待确认/3已做单/4已递交/5对公认款中/6二维码/7待补充/8已作废/9待递交")
    business_type = Column(TINYINT, nullable=True, comment="1新投/2批改")
    insurance_company = Column(String(50), nullable=True, comment="保险公司")
    customer_company = Column(String(100), nullable=True, comment="客户公司")
    creator = Column(String(50), nullable=True, comment="提单人")
    user_id = Column(BigInteger, nullable=True, comment="提单人ID")
    operator = Column(String(50), nullable=True, comment="做单员")
    operator_id = Column(BigInteger, nullable=True, comment="做单员ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class TaskComment(Base):
    """任务留言表"""
    __tablename__ = "task_comments"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(32), nullable=False, index=True, comment="关联任务")
    content = Column(Text, nullable=False, comment="留言内容")
    author_name = Column(String(50), nullable=True, comment="内勤姓名")
    author_id = Column(Integer, nullable=True, comment="内勤ID")
    created_at = Column(DateTime, server_default=func.now())


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(50), nullable=True)
    phone = Column(String(20), nullable=True, comment="手机号")
    password = Column(String(100), nullable=True, comment="密码（bcrypt哈希）")
    role = Column(Integer, default=1, comment="0管理员/1客服(提单人)/2内勤(做单人)")
    created_at = Column(DateTime, server_default=func.now())
