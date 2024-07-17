import os
import pathlib
import logging
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

    def log_config(self):
        logging.info(f"Database Configuration: USER={self.DB_USER}, "
                     f"HOST={self.DB_HOST}, PORT={self.DB_PORT}, NAME={self.DB_NAME}")
        logging.info(f"MINIO Configuration: ENDPOINT={self.MINIO_ENDPOINT}, "
                     f"BUCKET={self.MINIO_BUCKET}")
        logging.info(f"RabbitMQ Configuration: HOST={self.RABBITMQ_HOST}, "
                     f"PORT={self.RABBITMQ_PORT}, FORWARDING_QUEUE={self.FORWARDING_QUEUE}, "
                     f"FEEDBACK_QUEUE={self.FEEDBACK_QUEUE}")