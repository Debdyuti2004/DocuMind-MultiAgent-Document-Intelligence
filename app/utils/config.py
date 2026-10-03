"""Configuration settings for DocuMind Document Intelligence System."""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application configuration settings loaded from environment or defaults."""
    
    # Project Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    DATA_DIR: Path = BASE_DIR / "data"
    UPLOAD_DIR: Path = DATA_DIR / "uploads"
    PROCESSED_DIR: Path = DATA_DIR / "processed"
    CHROMA_PATH: Path = DATA_DIR / "chroma"
    SAMPLE_DOCS_DIR: Path = DATA_DIR / "sample_docs"

    # LLM Settings
    LLM_PROVIDER: str = Field(default="ollama", description="ollama, openai, or mock")
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API Key")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1")
    OPENAI_MODEL: str = Field(default="gpt-4o-mini")
    
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llama3")

    # Embeddings & Vector Store
    EMBEDDING_MODEL: str = Field(default="all-MiniLM-L6-v2")
    CHROMA_COLLECTION_NAME: str = Field(default="documind_docs")
    
    # Chunking & Retrieval parameters
    CHUNK_SIZE: int = Field(default=800, description="Target chunk character size")
    CHUNK_OVERLAP: int = Field(default=150, description="Chunk overlap characters")
    TOP_K: int = Field(default=5, description="Default number of retrieved chunks")
    SIMILARITY_THRESHOLD: float = Field(default=0.35, description="Min cosine similarity score")

    # App Settings
    APP_HOST: str = "127.0.0.1"
    APP_PORT: int = 8000
    DEBUG: bool = False
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        self.CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.SAMPLE_DOCS_DIR.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()
