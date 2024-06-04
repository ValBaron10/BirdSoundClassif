import asyncio
import json
from unittest.mock import Mock, patch

import pytest
from app_utils.rabbitmq import (
    connect_to_rabbitmq,
    consume_feedback_messages,
    consume_messages,
    get_rabbit_connection,
    process_feedback_message,
    publish_message,
)
from minio import Minio  # Assuming you have the Minio library installed


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
    return mock_channel


@pytest.fixture()
def minio_client():
    mock_minio_client = Mock(spec=Minio)
    return mock_minio_client


def test_connect_to_rabbitmq(rabbit_connection):
    # Test the connect_to_rabbitmq function
    host = "localhost"
    port = 5672
    conn = connect_to_rabbitmq(host, port)
    assert conn == rabbit_connection


def test_get_rabbit_connection(rabbit_connection):
    # Test the get_rabbit_connection function
    host = "localhost"
    port = 5672
    conn = get_rabbit_connection(host, port)
    assert conn == rabbit_connection


def test_publish_message(rabbit_channel):
    # Test the publish_message function
    queue_name = "test_queue"
    message = {
        "json_minio_path": "/path/to/file.json",
        "email": "example@example.com",
        "ticket_number": "ABC123",
    }
    publish_message(rabbit_channel, queue_name, message)
    rabbit_channel.basic_publish.assert_called_once_with(
        exchange="", routing_key=queue_name, body=json.dumps(message)
    )
    assert rabbit_channel.basic_publish.call_count == 1
    assert (
        rabbit_channel.basic_publish.call_args[1]["exchange"] == ""
    )  # Assert the exchange is empty
    assert (
        rabbit_channel.basic_publish.call_args[1]["routing_key"] == queue_name
    )  # Assert the routing key is correct
    assert rabbit_channel.basic_publish.call_args[1]["body"] == json.dumps(
        message
    )  # Assert the body is correct


def test_consume_messages(rabbit_channel):
    # Test the consume_messages function
    queue_name = "test_queue"
    callback_mock = Mock()
    consume_messages(rabbit_channel, queue_name, callback_mock)
    rabbit_channel.basic_consume.assert_called_once_with(
        queue=queue_name,
        on_message_callback=rabbit_channel.basic_consume.call_args[1][
            "on_message_callback"
        ],
    )
    rabbit_channel.start_consuming.assert_called_once()
    assert rabbit_channel.basic_consume.call_count == 1
    assert rabbit_channel.start_consuming.call_count == 1
    assert (
        rabbit_channel.basic_consume.call_args[1]["queue"] == queue_name
    )  # Assert the queue name is correct
    assert callable(
        rabbit_channel.basic_consume.call_args[1]["on_message_callback"]
    )  # Assert the callback is a callable


def test_process_feedback_message(minio_client):
    # Test the process_feedback_message function
    body = json.dumps(
        {
            "json_minio_path": "/path/to/file.json",
            "email": "example@example.com",
            "ticket_number": "ABC123",
        }
    )
    minio_bucket = "test_bucket"
    with patch("app_utils.rabbitmq.send_email") as mock_send_email, \
         patch("app_utils.rabbitmq.fetch_file_contents_from_minio") as mock_fetch_file:
        mock_fetch_file.return_value = "/tmp/tmpm_alnmvc"
        process_feedback_message(body.encode(), minio_client, minio_bucket)
        mock_send_email.assert_called_once_with(
            "example@example.com",
            "/tmp/tmpm_alnmvc",
            "ABC123",
        )
        assert mock_send_email.call_count == 1

@pytest.mark.asyncio()
async def test_consume_feedback_messages(rabbit_channel, minio_client):
    # Test the consume_feedback_messages function
    feedback_queue = "feedback_queue"
    minio_bucket = "test_bucket"
    body1 = json.dumps(
        {
            "json_minio_path": "/path/to/file1.json",
            "email": "example1@example.com",
            "ticket_number": "ABC123",
        }
    )
    body2 = json.dumps(
        {
            "json_minio_path": "/path/to/file2.json",
            "email": "example2@example.com",
            "ticket_number": "DEF456",
        }
    )
    stop_event = asyncio.Event()
    with patch(
        "app_utils.rabbitmq.process_feedback_message"
    ) as mock_process_feedback_message:
        # Case 1: No message available
        rabbit_channel.basic_get.return_value = (None, None, None)
        await asyncio.sleep(1.1)  # Wait for the loop to sleep for 1 second
        assert mock_process_feedback_message.call_count == 0

        # Case 2: Single message available
        rabbit_channel.basic_get.side_effect = [
            (Mock(delivery_tag=1), None, body1.encode()),
            asyncio.CancelledError(),  # Simulate loop exit
        ]
        try:
            await consume_feedback_messages(
                rabbit_channel,
                feedback_queue,
                minio_client,
                minio_bucket,
                stop_event=stop_event,
            )
        except asyncio.CancelledError:
            pass  # Ignore CancelledError
        mock_process_feedback_message.assert_called_once_with(
            body1.encode(), minio_client, minio_bucket
        )
        rabbit_channel.basic_ack.assert_called_once_with(delivery_tag=1)

        # Case 3: Multiple messages available
        mock_process_feedback_message.reset_mock()
        rabbit_channel.basic_get.side_effect = [
            (Mock(delivery_tag=2), None, body1.encode()),
            (Mock(delivery_tag=3), None, body2.encode()),
            asyncio.CancelledError(),  # Simulate loop exit
        ]
        try:
            await consume_feedback_messages(
                rabbit_channel,
                feedback_queue,
                minio_client,
                minio_bucket,
                stop_event=stop_event,
            )
        except asyncio.CancelledError:
            pass  # Ignore CancelledError
        assert mock_process_feedback_message.call_count == 2
        mock_process_feedback_message.assert_any_call(
            body1.encode(), minio_client, minio_bucket
        )
        mock_process_feedback_message.assert_any_call(
            body2.encode(), minio_client, minio_bucket
        )
        rabbit_channel.basic_ack.assert_any_call(delivery_tag=2)
        rabbit_channel.basic_ack.assert_any_call(delivery_tag=3)

        # Case 4: Stop event set
        stop_event.set()
        rabbit_channel.basic_get.side_effect = [
            (Mock(delivery_tag=4), None, body1.encode()),
            (None, None, None),  # No more messages
        ]
        await consume_feedback_messages(
            rabbit_channel,
            feedback_queue,
            minio_client,
            minio_bucket,
            stop_event=stop_event,
        )
        assert mock_process_feedback_message.call_count == 3
        mock_process_feedback_message.assert_called_with(
            body1.encode(), minio_client, minio_bucket
        )
        rabbit_channel.basic_ack.assert_called_with(delivery_tag=4)
