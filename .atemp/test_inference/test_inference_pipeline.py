import sys
import json
from unittest.mock import MagicMock, patch

# Function to recursively mock a module and its submodules
def recursive_mock(module_name, version="0.17.0"):
    mock = MagicMock()
    mock.__version__ = version
    sys.modules[module_name] = mock
    for submodule in [
        'torch', 'torch.nn', 'torch.nn.functional', 'torch.distributed',
        'torchvision', 'torchvision.models', 'torchvision.models._utils',
        'torchvision.transforms', 'torchaudio', "scipy", "scipy.optimize"
    ]:
        sys.modules[submodule] = mock

# Recursively mock torch and torchvision libraries
recursive_mock('torch')
recursive_mock('torchvision')
recursive_mock('torchaudio')
recursive_mock('scipy')


import pytest
from app.inference.main import callback, run_inference_pipeline

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
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    return

@patch("app.inference.main.run_inference_pipeline")
def test_callback(mock_run_inference_pipeline, set_env_var):
    body = json.dumps({
        "minio_path": "path/to/audio.wav",
        "email": "test@example.com",
        "ticket_number": "12345"
    }).encode()

    callback(body)

    mock_run_inference_pipeline.assert_called_once_with(
        "path/to/audio.wav", "test@example.com", "12345"
    )

@patch("app.inference.main.minio_client")
@patch("app.inference.main.ModelServer")
@patch("app.inference.main.publish_message")
@patch("app.inference.main.write_file_to_minio")
def test_run_inference_pipeline(mock_write_file_to_minio, mock_publish_message, MockModelServer, mock_minio_client, set_env_var):
    mock_minio_client.fget_object = MagicMock()
    mock_model_server_instance = MockModelServer.return_value
    mock_model_server_instance.get_classification.return_value = {"bird_species": "sparrow"}

    run_inference_pipeline("path/to/audio.wav", "test@example.com", "12345")

    mock_minio_client.fget_object.assert_called_once_with(
        "minio-bucket-name", "audio.wav", "/tmp/audio.wav"
    )
    mock_model_server_instance.load.assert_called_once()
    mock_model_server_instance.get_classification.assert_called_once_with("/tmp/audio.wav")
    mock_write_file_to_minio.assert_called_once()
    mock_publish_message.assert_called_once()