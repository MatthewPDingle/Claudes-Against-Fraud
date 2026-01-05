"""
Configuration management for Claudes Against Fraud API
"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""

    # Application
    APP_NAME: str = "Claudes Against Fraud API"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API
    API_V1_PREFIX: str = "/v1"
    ALLOWED_HOSTS: list[str] = ["*"]
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Database
    DATABASE_URL: str = "postgresql://caf_user:changeme@localhost:5432/claudes_against_fraud"
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # MinIO / S3
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "evidence"
    MINIO_SECURE: bool = False

    # Authentication
    SECRET_KEY: str = "changeme-secret-key-for-development-only"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_STORAGE_URL: str = "redis://localhost:6379/1"

    # Trust Levels and Rate Limits
    RATE_LIMIT_NEWCOMER: int = 10  # requests per minute
    RATE_LIMIT_CONTRIBUTOR: int = 30
    RATE_LIMIT_TRUSTED: int = 100
    RATE_LIMIT_EXPERT: int = 500

    # Task Queue
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Consensus Settings
    MIN_VERIFICATIONS_LOW_IMPACT: int = 3
    MIN_VERIFICATIONS_MEDIUM_IMPACT: int = 4
    MIN_VERIFICATIONS_HIGH_IMPACT: int = 5
    CONSENSUS_THRESHOLD_LOW: float = 0.6
    CONSENSUS_THRESHOLD_MEDIUM: float = 0.75
    CONSENSUS_THRESHOLD_HIGH: float = 0.9

    # Publication
    PUBLICATION_CONFIDENCE_THRESHOLD: float = 0.7
    PUBLICATION_CONSENSUS_THRESHOLD: float = 0.75

    # Security
    API_KEY_LENGTH: int = 64
    PASSWORD_MIN_LENGTH: int = 12

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
