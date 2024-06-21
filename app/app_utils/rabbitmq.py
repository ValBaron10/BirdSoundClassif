"""RabbitMQ Utility Module.

This module provides utility functions for interacting with RabbitMQ message broker. It
includes functions for connecting to RabbitMQ, publishing messages, consuming messages,
and processing feedback messages.

"""

import asyncio
import json
import logging
import time
from pydantic import ValidationError
import pika

from app_utils.amqp_schemas import FeedbackMessage
from app_utils.minio import fetch_file_contents_from_minio
from app_utils.smtplib import send_email


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# Global variable to manage RabbitMQ connection
rabbit_connection = None


def connect_to_rabbitmq(
    host, port, max_retries=5, retry_delay=5
) -> pika.BlockingConnection:
    """Connect to RabbitMQ with automatic retries.

    Args:
    ----
        host (str): The hostname or IP address of the RabbitMQ server.
        port (int): The port number of the RabbitMQ server.
        max_retries (int, optional): The maximum number of connection retries.
        retry_delay (int, optional): The delay in seconds between each retry attempt.

    Returns:
    -------
        pika.BlockingConnection: The established connection to RabbitMQ.

    Raises:
    ------
        Exception: If the connection to RabbitMQ fails after the specified number of retries.

    """
    global rabbit_connection
    retry_count = 0

    while retry_count < max_retries:
        logging.info(
            f"Attempting to connect to RabbitMQ (Attempt {retry_count + 1}/{max_retries})"
        )
        try:
            rabbit_connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=host, port=port)
            )
            logging.info("Successfully connected to RabbitMQ")
            return rabbit_connection
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(
                f"Error connecting to RabbitMQ: {e!s}. Retrying in {retry_delay} seconds..."
            )
            retry_count += 1
            time.sleep(retry_delay)
            if retry_count == max_retries:
                logging.critical(
                    "Failed to connect to RabbitMQ after multiple retries."
                )
                raise Exception("Failed to connect to RabbitMQ after multiple retries.")


def get_rabbit_connection(host, port) -> pika.BlockingConnection:
    """Get the current RabbitMQ connection or establishes a new one if necessary.

    Returns
    -------
        pika.BlockingConnection: The active RabbitMQ connection.

    """
    global rabbit_connection
    logging.info("Checking RabbitMQ connection")
    if rabbit_connection is None or rabbit_connection.is_closed:
        logging.info(
            "RabbitMQ connection is None or closed. Establishing a new connection."
        )
        connect_to_rabbitmq(host, port)
        logging.info("RabbitMQ connection established.")
    else:
        logging.info("RabbitMQ connection is active.")
    return rabbit_connection


def publish_message(channel, queue_name, message) -> None:
    """Publish a message to a specified RabbitMQ queue.

    Args:
    ----
        channel: The active channel of the RabbitMQ connection.
        queue_name (str): The name of the queue where the message will be published.
        message (dict): The message to be published, containing the MinIO path, email, and ticket number.

    Returns:
    -------
        None

    """
    logging.info(f"Preparing to publish message to queue: {queue_name}")
    try:
        channel.basic_publish(
            exchange="", routing_key=queue_name, body=json.dumps(message)
        )
        logging.info(f"Published message: {message}")
    except Exception as e:
        logging.error(f"Failed to publish message: {e!s}")


def consume_messages(channel, queue_name, callback) -> None:
    """Consume messages from a specified RabbitMQ queue
       and invokes a callback function for each message.

    Args:
    ----
        channel: The active channel of the RabbitMQ connection.
        queue_name (str): The name of the queue to consume messages from.
        callback (function): The callback function to be invoked
                             for each received message.
                             The function should accept a single argument,
                             which is the message body.

    Returns:
    -------
        None

    """  # noqa: D205

    def on_message(ch, method, properties, body):
        """Nest a callback function invoked for each received message.

        Args:
        ----
            ch: The channel object.
            method: The delivery method.
            properties: The message properties.
            body: The message body.

        """
        callback(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name, on_message_callback=on_message)
    channel.start_consuming()



async def process_feedback_message(body, minio_client, minio_bucket) -> None:
    """Process a feedback message received from RabbitMQ.

    This function extracts the email, annotations MinIO path, and ticket number from the message body.
    It then sends an email using the extracted information and the provided MinIO client and bucket.

    Args:
    ----
        body (bytes): The body of the feedback message received from RabbitMQ.
        minio_client (Minio): The MinIO client instance used to interact with MinIO.
        minio_bucket (str): The name of the MinIO bucket where the annotations file is stored.

    Returns:
    -------
        None

    """
    from api import crud
    from api.database import get_async_session
    try:
        feedback_message = FeedbackMessage.parse_raw(body.decode())
    except ValidationError as e:
        logging.error(f"Message validation error: {e}")
        return

    email = feedback_message.email
    annotations_minio_path = feedback_message.annotations_minio_path
    ticket_number = feedback_message.ticket_number
    soundfile_minio_path = feedback_message.soundfile_minio_path
    spectrogram_minio_path = feedback_message.spectrogram_minio_path
    classification_score = feedback_message.classification_score

    async with get_async_session() as session:
        service_call = await crud.create_service_call(
            session, email, ticket_number, soundfile_minio_path
        )
        await crud.create_inference_result(
            session, 
            service_call.id, 
            annotations_minio_path, 
            spectrogram_minio_path, 
            classification_score
        )

    send_email(email, annotations_minio_path, ticket_number, minio_client, minio_bucket)

async def consume_feedback_messages(
    rabbitmq_channel, feedback_queue, minio_client, minio_bucket, stop_event=None
) -> None:
    """Consume feedback messages from the specified RabbitMQ queue.

    This function continuously consumes feedback messages
    from the specified RabbitMQ queue.
    For each received message, it processes the message
    using the `process_feedback_message` function
    and acknowledges the message.
    If no message is available, it waits for 1 second before checking again.
    If the `stop_event` is set, it stops consuming messages after processing the current message.

    Args:
    ----
        rabbitmq_channel (pika.adapters.blocking_connection.BlockingChannel):
            The RabbitMQ channel used for consuming messages.
        feedback_queue (str): The name of the RabbitMQ queue to consume feedback messages from.
        minio_client (Minio): The MinIO client instance used to interact with MinIO.
        minio_bucket (str): The name of the MinIO bucket where the JSON files are stored.
        stop_event (asyncio.Event, optional): An event object that can be used to stop consuming messages.

    Returns:
    -------
        None

    """
    while True:
        method_frame, _, body = rabbitmq_channel.basic_get(queue=feedback_queue)
        if method_frame:
            process_feedback_message(body, minio_client, minio_bucket)
            rabbitmq_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            if stop_event and stop_event.is_set():
                break
        else:
            await asyncio.sleep(1)  # Wait for 1 second before checking again
