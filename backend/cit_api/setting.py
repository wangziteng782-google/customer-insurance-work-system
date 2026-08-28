from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "客服保险工单系统"
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/insurance_work"

    # 千问 API 配置
    QWEN_API_KEY: str = "sk-b7c5835b066f44e0b224bf760e1cd9a2"
    QWEN_API_URL: str = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    QWEN_MODEL: str = "qwen-turbo"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
