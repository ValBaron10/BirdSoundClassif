import json
import pytest
import pika
import time
from unittest.mock import MagicMock
from tests.utils.docker import start_inference_container
from tests.fixtures.utils_fixtures import set_env_var, mock_minio_client, mock_rabbitmq_channel

@pytest.fixture(scope="session")
def inference_container():
    container = start_inference_container()
    yield container
    container.stop()
    container.remove()

@pytest.mark.usefixtures("inference_container")
def test_inference_pipeline(set_env_var, mock_minio_client, mock_rabbitmq_channel):
    # Mock MinIO client
    mock_minio_client.fput_object.return_value = None
    mock_minio_client.stat_object.return_value = MagicMock()

    # Mock RabbitMQ connection and channel
    mock_rabbitmq_channel.basic_publish.return_value = None

    # Send a message to the inference queue
    message = {
        "minio_path": "mock_audio.wav",
        "email": "test@example.com",
        "ticket_number": "12345"
    }
    mock_rabbitmq_channel.basic_publish(
        exchange='',
        routing_key='api-to-inf-queue',
        body=json.dumps(message)
    )

    # Wait for the inference to complete and check the output
    time.sleep(10)  # Adjust the sleep time as needed

    # Check if the output file exists in MinIO
    output_file_path = "path/to/output.json"
    found = mock_minio_client.stat_object("minio-bucket-name", output_file_path)
    assert found is not None

    # Clean up
    mock_minio_client.remove_object("minio-bucket-name", "mock_audio.wav")
    mock_minio_client.remove_object("minio-bucket-name", output_file_path)