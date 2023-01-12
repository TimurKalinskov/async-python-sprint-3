from pydantic import BaseSettings


class Settings(BaseSettings):
    DB_NAME: str = 'db_chat.db'
    TZ: str = 'Europe/Moscow'
    HOST: str = '127.0.0.1'
    PORT: int = 8000
    LIMIT_SHOW_MESSAGES: int = 20
    LIFETIME_MESSAGES: int = 60
    LIMIT_MESSAGES: int = 20
    UPDATE_PERIOD: int = 60

    class Config:
        case_sensitive = True
        env_file = '.env'
        env_file_encoding = 'utf-8'


settings = Settings()
