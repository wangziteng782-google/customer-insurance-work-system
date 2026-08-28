from sqlalchemy import Column, Integer, String, Numeric, Boolean, Date, DateTime, Text, func
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class NewPolicy(Base):
    """新投表"""
    __tablename__ = "new_policies"

    id = Column(Integer, primary_key=True, autoincrement=True, comment="主键")

    # 业务字段
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

    # 公共字段
    creator = Column(String(50), nullable=True, comment="创建人")
    handler = Column(String(50), nullable=True, comment="做单人")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    completed_at = Column(DateTime, nullable=True, comment="完成时间")
