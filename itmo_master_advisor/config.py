import os
from dotenv import load_dotenv
from pydantic import BaseSettings

load_dotenv()

class Settings(BaseSettings):
    # API Keys
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    
    # URLs
    AI_PROGRAM_URL: str = "https://abit.itmo.ru/program/master/ai"
    AI_PRODUCT_URL: str = "https://abit.itmo.ru/program/master/ai_product"
    
    # Model settings
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    LLM_MODEL: str = "gpt-4-turbo-preview"
    TEMPERATURE: float = 0.3
    
    # RAG settings
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 5
    
    # Paths
    DATA_DIR: str = "data"
    CHROMA_DIR: str = "chroma_db"

settings = Settings()