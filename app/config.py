from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./kith.db"

    JWT_SECRET: str = "change-this-secret"
    JWT_ACCESS_EXPIRES_MINUTES: int = 30
    JWT_REFRESH_EXPIRES_DAYS: int = 7

    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL_SMART: str = "qwen/qwen-2.5-72b-instruct"
    OPENROUTER_MODEL_FAST: str = "qwen/qwen-2.5-7b-instruct"

    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"

    LLM_MAX_TOOL_ITERATIONS: int = 5
    LLM_CHAT_HISTORY_LIMIT: int = 20
    LLM_REQUEST_TIMEOUT: int = 30

    PORT: int = 8000
    ENV: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
