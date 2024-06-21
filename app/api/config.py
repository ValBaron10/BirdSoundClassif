import os
import pathlib
from typing import ClassVar

class BaseConfig:

    BASE_DIR: pathlib.Path = pathlib.Path(__file__).parent.parent

    # Construct DATABASE_URL using environment variables
    DB_USER = os.getenv("POSTGRES_USER")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD")
    DB_HOST = os.getenv("POSTGRES_HOST")
    DB_PORT = os.getenv("POSTGRES_PORT")
    DB_NAME = os.getenv("POSTGRES_DB")

    ASYNC_DATABASE_URL: ClassVar[str] = (
        f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    DATABASE_URL: ClassVar[str] = (
        f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    
    MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
    MINIO_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
    MINIO_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET")
    
    RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
    RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    FORWARDING_QUEUE = os.getenv("RABBITMQ_QUEUE_API2INF")
    FEEDBACK_QUEUE = os.getenv("RABBITMQ_QUEUE_INF2API")
    
    