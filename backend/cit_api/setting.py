from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "客服保险工单系统"
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/insurance_work"

    # 千问 API 配置
    QWEN_API_KEY: str = "sk-b7c5835b066f44e0b224bf760e1cd9a2"
    QWEN_API_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    QWEN_MODEL: str = "qwen-turbo"

    # 七牛云配置
    QINIU_ACCESS_KEY: str = "Rwoba5bAn0msGlZ6fr8JIZsYjk6vC3qwY38GYNUZ"
    QINIU_SECRET_KEY: str = "Jo2APlhaa7m_wfqhJASd_0uV9Kg6wCfieZKgHL6n"
    QINIU_BUCKET: str = "yiti-zt-price"
    QINIU_DOMAIN: str = "http://price.yitipeijian.com"  # 例如 https://cdn.xxx.com

    # 认证密钥（生产环境通过 .env 覆盖）
    AUTH_SECRET: str = "change-me-to-long-random-string"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
