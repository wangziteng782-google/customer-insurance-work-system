from sqlalchemy import Column, BigInteger, String, Text, DateTime, func, JSON, Integer, Numeric, Boolean, Date, ForeignKey
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
    status = Column(TINYINT, nullable=False, default=0, comment="0待处理/1处理中/2已完成/3已关闭")
    business_type = Column(TINYINT, nullable=True, comment="1新投/2批改")
    insurance_company = Column(String(50), nullable=True, comment="保险公司")
    customer_company = Column(String(100), nullable=True, comment="客户公司")
    creator = Column(String(50), nullable=True, comment="提单人")
    user_id = Column(BigInteger, nullable=True, comment="提单人ID")
    operator = Column(String(50), nullable=True, comment="做单员")
    operator_id = Column(BigInteger, nullable=True, comment="做单员ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")


class NewPolicy(Base):
    """新投表"""
    __tablename__ = "new_policies"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    company_name = Column(String(100), nullable=False, comment="公司名称")
    source = Column(String(50), nullable=True, comment="来源")
    job_type = Column(String(50), nullable=True, comment="工种")
    plan = Column(String(100), nullable=True, comment="方案")
    is_renewal = Column(String(20), nullable=True, comment="续保/新投")
    specified_effective = Column(Boolean, default=False, comment="是否指定生效")
    discovery_date = Column(Date, nullable=True, comment="发现日期")
    insurance_type = Column(String(50), nullable=True, comment="险种")
    annual_salary = Column(Numeric(12, 2), nullable=True, comment="年薪")
    remarks = Column(Text, nullable=True, comment="备注")
    qualification = Column(String(100), nullable=True, comment="资质")
    file_paths = Column(Text, nullable=True, comment="上传文件路径(JSON数组)")
    status = Column(String(20), default="待完成", comment="状态：待完成/已完成/有异常")
    creator = Column(String(50), nullable=True, comment="创建人")
    handler = Column(String(50), nullable=True, comment="做单人")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(50), nullable=True)
    role = Column(String(20), default="staff")
    created_at = Column(DateTime, server_default=func.now())


class Endorsement(Base):
    """批改表"""
    __tablename__ = "endorsements"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")
    new_policy_id = Column(Integer, ForeignKey("new_policies.id"), nullable=False, comment="关联新投id")
    company_name = Column(String(100), nullable=False, comment="公司名称")
    job_type = Column(String(50), nullable=True, comment="工种")
    specified_effective = Column(Boolean, default=False, comment="是否指定生效")
    insurance_type = Column(String(50), nullable=True, comment="险种")
    annual_salary = Column(Numeric(12, 2), nullable=True, comment="年薪")
    remarks = Column(Text, nullable=True, comment="备注")
    file_paths = Column(Text, nullable=True, comment="上传文件路径(JSON数组)")
    status = Column(String(20), default="待完成", comment="状态：待完成/已完成/有异常")
    creator = Column(String(50), nullable=True, comment="创建人")
    handler = Column(String(50), nullable=True, comment="做单人")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
