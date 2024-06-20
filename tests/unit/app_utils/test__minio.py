import pytest
from unittest.mock import MagicMock, call
from app.app_utils.minio import ensure_bucket_exists, write_file_to_minio, fetch_file_from_minio
import io

@pytest.fixture
def mock_minio_client():
    return MagicMock()

def test_ensure_bucket_exists_bucket_exists(mock_minio_client):
    # Mock bucket_exists to return True
    mock_minio_client.bucket_exists.return_value = True

    ensure_bucket_exists(mock_minio_client, "test_bucket")

    # Assertions
    mock_minio_client.bucket_exists.assert_called_once_with("test_bucket")
    mock_minio_client.make_bucket.assert_not_called()

def test_ensure_bucket_exists_bucket_does_not_exist(mock_minio_client):
    # Mock bucket_exists to return False
    mock_minio_client.bucket_exists.return_value = False

    ensure_bucket_exists(mock_minio_client, "test_bucket")

    # Assertions
    mock_minio_client.bucket_exists.assert_called_once_with("test_bucket")
    mock_minio_client.make_bucket.assert_called_once_with("test_bucket")

def test_write_file_to_minio_bytes(mock_minio_client):
    # Call the function with bytes data
    write_file_to_minio(mock_minio_client, "test_bucket", "test_file.txt", b"test content")

    # Assertions
    mock_minio_client.put_object.assert_called_once()
    args, kwargs = mock_minio_client.put_object.call_args
    assert args[0] == "test_bucket"
    assert args[1] == "test_file.txt"
    assert isinstance(args[2], io.BytesIO)
    assert args[2].read() == b"test content"
    assert kwargs['length'] == len(b"test content")

def test_write_file_to_minio_file_like(mock_minio_client):
    # Create a file-like object
    file_like = io.BytesIO(b"test content")

    # Call the function with file-like data
    write_file_to_minio(mock_minio_client, "test_bucket", "test_file.txt", file_like)

    # Assertions
    mock_minio_client.put_object.assert_called_once()
    args, kwargs = mock_minio_client.put_object.call_args
    assert args[0] == "test_bucket"
    assert args[1] == "test_file.txt"
    assert args[2] == file_like
    assert kwargs['length'] == len(b"test content")

def test_fetch_file_from_minio_success(mock_minio_client):
    # Call the function
    result = fetch_file_from_minio(mock_minio_client, "test_bucket", "test_file.txt", "/local/path/test_file.txt")

    assert result is True
    mock_minio_client.fget_object.assert_called_once_with("test_bucket", "test_file.txt", "/local/path/test_file.txt")

def test_fetch_file_from_minio_failure(mock_minio_client):
    # Mock fget_object to raise an exception
    mock_minio_client.fget_object.side_effect = Exception("Error fetching file")

    result = fetch_file_from_minio(mock_minio_client, "test_bucket", "test_file.txt", "/local/path/test_file.txt")

    assert result is False
    mock_minio_client.fget_object.assert_called_once_with("test_bucket", "test_file.txt", "/local/path/test_file.txt")