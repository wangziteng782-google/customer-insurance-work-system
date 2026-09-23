from sqlalchemy import Column, BigInteger, String, Text, DateTime, func, JSON, Integer, Index
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
    recalled_at = Column(DateTime, nullable=True, comment="撤回时间，NULL=正常（逻辑删除）")


class InsuranceTask(Base):
    """任务主表"""
    __tablename__ = "insurance_tasks"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    task_id = Column(String(32), nullable=False, unique=True, comment="任务ID")
    status = Column(TINYINT, nullable=False, default=1, comment="1进行中/2待确认/3已做单/4已递交/5对公认款中/6二维码/7待补充/8已作废/9待递交/10进行中(修改,客服在非进行中状态发消息时自动置入,不可手动设置)")
    business_type = Column(TINYINT, nullable=True, comment="1新投/2批改")
    insurance_company = Column(String(50), nullable=True, comment="保险公司")
    customer_company = Column(String(100), nullable=True, comment="客户公司")
    creator = Column(String(50), nullable=True, comment="提单人")
    user_id = Column(BigInteger, nullable=True, comment="提单人ID")
    operator = Column(String(50), nullable=True, comment="做单员")
    operator_id = Column(BigInteger, nullable=True, comment="做单员ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    last_msg_at = Column(DateTime, nullable=True, comment="最新消息时间（发消息时同步更新，用于红点判断）")


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
    role = Column(Integer, default=1, comment="0管理员/1客服(提单人)/11客服主管/2内勤(做单人)/22内勤主管")
    can_manage_dropdowns = Column(TINYINT, default=0, comment="可管理下拉选项")
    created_at = Column(DateTime, server_default=func.now())


class DropdownOption(Base):
    """下拉选项表"""
    __tablename__ = "dropdown_options"

    id       = Column(BigInteger, primary_key=True, autoincrement=True)
    category = Column(String(30), nullable=False, comment="分类标识")
    value    = Column(String(100), nullable=False, comment="选项值")
    sort     = Column(Integer, default=0, comment="排序")


class Tag(Base):
    """用户自定义标签"""
    __tablename__ = "tags"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, nullable=False, index=True, comment="创建者")
    name       = Column(String(30), nullable=False, comment="标签名")
    color      = Column(String(20), default="#1677ff", comment="颜色")
    created_at = Column(DateTime, server_default=func.now())


class TaskTag(Base):
    """任务-标签关联表"""
    __tablename__ = "task_tags"

    id         = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id    = Column(Integer, nullable=False, comment="谁加的")
    task_id    = Column(String(32), nullable=False, comment="哪个任务")
    tag_id     = Column(BigInteger, nullable=False, comment="哪个标签")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_user_task", "user_id", "task_id"),
        Index("idx_task", "task_id"),
    )