import pytest
from tests.utils.docker import start_inference_container

@pytest.fixture(scope="session")
def inference_container():
    container = start_inference_container()
    yield container
    container.stop()
    container.remove()

@pytest.fixture(scope="function")
def set_env_var(monkeypatch):
    env_vars = {
        "MINIO_ENDPOINT": "http://minioserver:9000",
        "AWS_ACCESS_KEY_ID": "minio-access-key",
        "AWS_SECRET_ACCESS_KEY": "minio-secret-key",
        "MINIO_BUCKET": "minio-bucket-name",
        "RABBITMQ_HOST": "rabbitmq",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_QUEUE_API2INF": "api-to-inf-queue",
        "RABBITMQ_QUEUE_INF2API": "inf-to-api-queue",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)