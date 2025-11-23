import os
from typing import List, Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置"""
    
    # DeepSeek 配置 (原OpenAI配置)
    openai_api_key: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    
    # 服务器配置
    host: str = "localhost"
    port: int = 8000
    debug: bool = True
    
    # CORS 配置
    allowed_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # 日志配置
    log_level: str = "INFO"
    log_file: str = "logs/app.log"
    
    # 模型配置
    default_model: str = "deepseek-chat"
    max_tokens: int = 2048
    temperature: float = 1.0
    
    # ModelScope 配置 (用于通义千问等模型)
    modelscope_api_key: str = "ms-f34cc515-37b3-41a6-ac34-2205a12517e7"
    modelscope_base_url: str = "https://api-inference.modelscope.cn/v1"
    # 可选第三方工具 API keys
    serpapi_api_key: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# 创建全局配置实例
settings = Settings()