import asyncio
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile


@pytest.fixture()
def mock_upload_file():
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.wav"
    mock_file.content_type = "audio/wav"

    # Create a future object and set its result to the file content
    future = asyncio.Future()
    future.set_result(b"test file content")

    # Mock the read method to return the future
    mock_file.read.return_value = future
    return mock_file


@pytest.fixture()
def mock_minio_client():
    mock_client = MagicMock()
    # Simulate that the file does not exist in MinIO by raising an exception
    mock_client.stat_object.side_effect = Exception("File does not exist")
    return mock_client


@pytest.fixture()
def mock_rabbitmq_channel():
    return MagicMock()


@pytest.fixture()
def patch_env_vars(monkeypatch):
    monkeypatch.setenv("MINIO_ENDPOINT", "http://localhost:9000")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test_access_key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test_secret_key")
    monkeypatch.setenv("MINIO_BUCKET", "test_bucket")
    monkeypatch.setenv("RABBITMQ_HOST", "localhost")
    monkeypatch.setenv("RABBITMQ_PORT", "5672")
    monkeypatch.setenv("RABBITMQ_QUEUE_API2INF", "forwarding_queue")
    monkeypatch.setenv("RABBITMQ_QUEUE_INF2API", "feedback_queue")


@pytest.fixture()
def patch_mocks(monkeypatch, mock_minio_client, mock_rabbitmq_channel):
    mock_write_file_to_minio = MagicMock()
    mock_publish_message = MagicMock()
    mock_ensure_bucket_exists = MagicMock()
    mock_minio = MagicMock(return_value=mock_minio_client)

    monkeypatch.setattr("minio.Minio", mock_minio)
    monkeypatch.setattr(
        "app_utils.minio.ensure_bucket_exists", mock_ensure_bucket_exists
    )
    monkeypatch.setattr("app_utils.minio.write_file_to_minio", mock_write_file_to_minio)
    monkeypatch.setattr(
        "app_utils.rabbitmq.get_rabbit_connection",
        MagicMock(
            return_value=MagicMock(
                channel=MagicMock(return_value=mock_rabbitmq_channel)
            )
        ),
    )
    monkeypatch.setattr("app_utils.rabbitmq.publish_message", mock_publish_message)

    return (
        mock_minio_client,
        mock_rabbitmq_channel,
        mock_write_file_to_minio,
        mock_publish_message,
        mock_ensure_bucket_exists,
    )


@pytest.mark.asyncio()
async def test_upload_record(mock_upload_file, patch_env_vars, patch_mocks):
    (
        mock_minio_client,
        mock_rabbitmq_channel,
        mock_write_file_to_minio,
        mock_publish_message,
        mock_ensure_bucket_exists,
    ) = patch_mocks

    # Import the upload_record function after setting the environment variables and mocking the required objects
    from app.api.main import upload_record

    # Call the upload_record coroutine
    result = await upload_record(mock_upload_file, "test@example.com")

    # Assertions
    assert result["filename"] == "test.wav"
    assert result["message"] == "Fichier enregistré avec succès"
    assert result["email"] == "test@example.com"
    assert len(result["ticket_number"]) == 6

    # Verify that the minio_client was called correctly
    mock_minio_client.stat_object.assert_called_once_with("test_bucket", "test.wav")

    # Extract the result from the Future before making the assertion
    file_content = await mock_upload_file.read()
    mock_write_file_to_minio.assert_called_once_with(
        mock_minio_client, "test_bucket", "test.wav", file_content
    )

    # Verify that the publish_message function was called correctly
    mock_publish_message.assert_called_once_with(
        mock_rabbitmq_channel,
        "forwarding_queue",
        {
            "minio_path": "test_bucket/test.wav",
            "email": "test@example.com",
            "ticket_number": result["ticket_number"],
        },
    )

    # Verify that the ensure_bucket_exists function was called
    mock_ensure_bucket_exists.assert_called_once_with(mock_minio_client, "test_bucket")
