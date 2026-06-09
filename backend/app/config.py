"""
模块名称：应用配置
功能描述：统一管理所有环境变量和配置项，通过 Pydantic Settings 加载 .env 文件
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用配置类，自动从 .env 文件加载环境变量"""

    # 后端服务
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # MySQL 连接
    mysql_host: str = "localhost"
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: str = ""
    mysql_database: str = ""

    # Redis 连接
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

    @property
    def database_url(self) -> str:
        """生成异步数据库连接 URL"""
        # 使用 .env 中实际的 mysql_password，空密码时格式为 user:@host:port/db
        return f"mysql+aiomysql://{self.mysql_user}:{self.mysql_password}@{self.mysql_host}:{self.mysql_port}/{self.mysql_database}"

    @property
    def celery_broker_url(self) -> str:
        """Celery Broker URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def celery_result_backend(self) -> str:
        """Celery Result Backend URL"""
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db + 1}"


# 全局配置单例
settings = Settings()
