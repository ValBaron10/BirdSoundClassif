import os
import pytest
from minio import Minio
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from app.api.main import app  # import your FastAPI instance

@pytest.fixture(scope="function")
def set_env_var(monkeypatch):
    env_vars = {
        "MINIO_ENDPOINT": "http://minio-endpoint.com",
        "AWS_ACCESS_KEY_ID": "minio-access-key",
        "AWS_SECRET_ACCESS_KEY": "minio-secret-key",
        "MINIO_BUCKET": "minio-bucket-name",
        "RABBITMQ_HOST": "rabbitmq-host",
        "RABBITMQ_PORT": "5672",
        "RABBITMQ_QUEUE_API2INF": "api-to-inf-queue",
        "RABBITMQ_QUEUE_INF2API": "inf-to-api-queue",
        "SMTP_SERVER": "mailhog",
        "SMTP_PORT": "1025",
        "SENDER_EMAIL": "sender@example.com",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    yield

@pytest.fixture()
def test_app(set_env_var):  # Add set_env_var as a dependency
    return TestClient(app)

@pytest.fixture()
def mock_minio_client():
    with patch("app.api.main.minio_client") as mock:
        yield mock

@pytest.fixture()
def mock_rabbitmq_channel():
    with patch("app.api.main.rabbitmq_channel") as mock:
        yield mock


@pytest.fixture()
def mock_smtp():
    with patch("smtplib.SMTP") as mock:
        yield mock


"""
@pytest.fixture()
def test_app(set_env_var):  # Add set_env_var as a dependency
    return TestClient(app)

@pytest.fixture()
def rabbit_connection():
    with patch("pika.BlockingConnection") as mock_connection:
        mock_conn = Mock()
        mock_connection.return_value = mock_conn
        yield mock_conn

@pytest.fixture()
def rabbit_channel(rabbit_connection):
    mock_channel = Mock()
    rabbit_connection.channel.return_value = mock_channel
    yield mock_channel

@pytest.fixture()
def minio_client():
    mock_minio_client = Mock(spec=Minio)
    yield mock_minio_client
    """