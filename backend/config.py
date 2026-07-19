"""
config.py — Flask application configuration
Reads all settings from .env via python-dotenv
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ------------------------------------------------------------------
    # Flask core
    # ------------------------------------------------------------------
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key-change-me")
    DEBUG = os.getenv("FLASK_DEBUG", "False").lower() == "true"

    # ------------------------------------------------------------------
    # Database (PostgreSQL via SQLAlchemy)
    # ------------------------------------------------------------------
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:9699@localhost:5432/ai_pm_copilot",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": int(os.getenv("DB_POOL_SIZE", 10)),
        "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", 20)),
        "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", 30)),
        "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", 1800)),
        "pool_pre_ping": True,
    }

    # ------------------------------------------------------------------
    # JWT
    # ------------------------------------------------------------------
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-jwt-secret-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        hours=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES_HOURS", 24))
    )
    JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")

    # ------------------------------------------------------------------
    # File Upload / Ingestion
    # ------------------------------------------------------------------
    MAX_CSV_SIZE_MB = int(os.getenv("MAX_CSV_SIZE_MB", 10))
    MAX_CONTENT_LENGTH = MAX_CSV_SIZE_MB * 1024 * 1024  # Flask upload limit in bytes
    PIPELINE_AUTO_TRIGGER_THRESHOLD = int(
        os.getenv("PIPELINE_AUTO_TRIGGER_THRESHOLD", 5)
    )

    # ------------------------------------------------------------------
    # Module 3 NLP Pipeline
    # ------------------------------------------------------------------
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.85))
    NLP_MODEL = os.getenv("NLP_MODEL", "en_core_web_sm")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    PIPELINE_VERSION = os.getenv("PIPELINE_VERSION", "1.0.0")

    # ------------------------------------------------------------------
    # Module 5 Feature Request Aggregation
    # ------------------------------------------------------------------
    AGGREGATION_CLUSTER_THRESHOLD = int(
        os.getenv("AGGREGATION_CLUSTER_THRESHOLD", 2)
    )
    AGGREGATION_PROMPT_VERSION = os.getenv("AGGREGATION_PROMPT_VERSION", "1.0.0")

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG")
    LOG_TO_FILE = os.getenv("LOG_TO_FILE", "False").lower() == "true"
    LOG_FILE_PATH = os.getenv("LOG_FILE_PATH", "logs/app.log")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "postgresql://postgres:9699@localhost:5432/ai_pm_copilot_test"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_map.get(env, DevelopmentConfig)
