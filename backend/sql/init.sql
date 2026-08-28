-- ============================================
-- 客服保险工单系统 - 数据库初始化脚本
-- ============================================

-- 1. 创建数据库（如已存在则跳过）
CREATE DATABASE IF NOT EXISTS insurance_work
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_general_ci;

USE insurance_work;

-- 2. 建表 —— 新投
CREATE TABLE IF NOT EXISTS new_policies (
  id                   INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
  company_name         VARCHAR(100)    NOT NULL                COMMENT '公司名称',
  source               VARCHAR(50)     DEFAULT NULL             COMMENT '来源',
  job_type             VARCHAR(50)     DEFAULT NULL             COMMENT '工种',
  plan                 VARCHAR(100)    DEFAULT NULL             COMMENT '方案',
  is_renewal           VARCHAR(20)     DEFAULT NULL             COMMENT '续保/新投',
  specified_effective  TINYINT(1)      DEFAULT 0                COMMENT '是否指定生效',
  discovery_date       DATE            DEFAULT NULL             COMMENT '发现日期',
  insurance_type       VARCHAR(50)     DEFAULT NULL             COMMENT '险种',
  annual_salary        DECIMAL(12,2)   DEFAULT NULL             COMMENT '年薪',
  remarks              TEXT            DEFAULT NULL             COMMENT '备注',
  qualification        VARCHAR(100)    DEFAULT NULL             COMMENT '资质',
  file_paths            TEXT            DEFAULT NULL             COMMENT '上传文件路径(JSON)',
  creator              VARCHAR(50)     DEFAULT NULL             COMMENT '创建人',
  handler              VARCHAR(50)     DEFAULT NULL             COMMENT '做单人',
  created_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  completed_at         DATETIME        DEFAULT NULL             COMMENT '完成时间',
  INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='新投表';

-- 3. 建表 —— 批改
CREATE TABLE IF NOT EXISTS endorsements (
  id                   INT AUTO_INCREMENT PRIMARY KEY COMMENT '主键',
  new_policy_id        INT             NOT NULL                COMMENT '关联新投id',
  company_name         VARCHAR(100)    NOT NULL                COMMENT '公司名称',
  job_type             VARCHAR(50)     DEFAULT NULL             COMMENT '工种',
  specified_effective  TINYINT(1)      DEFAULT 0                COMMENT '是否指定生效',
  insurance_type       VARCHAR(50)     DEFAULT NULL             COMMENT '险种',
  annual_salary        DECIMAL(12,2)   DEFAULT NULL             COMMENT '年薪',
  remarks              TEXT            DEFAULT NULL             COMMENT '备注',
  file_paths            TEXT            DEFAULT NULL             COMMENT '上传文件路径(JSON)',
  creator              VARCHAR(50)     DEFAULT NULL             COMMENT '创建人',
  handler              VARCHAR(50)     DEFAULT NULL             COMMENT '做单人',
  created_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  completed_at         DATETIME        DEFAULT NULL             COMMENT '完成时间',
  INDEX idx_new_policy_id (new_policy_id),
  INDEX idx_created_at (created_at),
  CONSTRAINT fk_endorsement_new_policy FOREIGN KEY (new_policy_id) REFERENCES new_policies(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='批改表';
