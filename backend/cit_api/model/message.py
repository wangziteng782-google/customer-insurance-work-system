from sqlalchemy import Column, BigInteger, String, Text, DateTime, func, JSON, Integer

from cit_api.model.new_policy_model import Base


class ChatMessage(Base):
    """聊天记录表"""
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="主键")
    task_id = Column(String(32), nullable=False, index=True, comment="任务编号（系统生成）")
    content = Column(Text, nullable=False, comment="消息内容")
    msg_type = Column(String(10), nullable=False, default="user", comment="消息类型：user/system")
    insurance_company = Column(String(50), nullable=True, comment="保险公司")
    file_paths = Column(JSON, nullable=True, comment="附件路径列表")
    creator = Column(String(50), nullable=True, comment="创建人")
    user_id = Column(Integer, nullable=True, comment="创建人ID")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
