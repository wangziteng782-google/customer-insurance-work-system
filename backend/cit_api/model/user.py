from sqlalchemy import Column, Integer, String, DateTime, func

from cit_api.model.new_policy_model import Base


class User(Base):
    """用户表"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(50), nullable=True)
    role = Column(String(20), default="staff")
    created_at = Column(DateTime, server_default=func.now())
