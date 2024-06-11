"""RabbitMQ Utility Module.

This module provides utility functions for interacting with RabbitMQ message broker. It
includes functions for connecting to RabbitMQ, publishing messages, consuming messages,
and processing feedback messages.

"""

import asyncio
import json
import logging
import time

import pika

from app_utils.smtplib import send_email
from app_utils.minio import fetch_file_contents_from_minio

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



def process_feedback_message(body, local_file_path) -> None:
    """Process a feedback message received from RabbitMQ.

    This function extracts the email and ticket number from the message body.
    It then sends an email using the extracted information and the provided local file path.

    Args:
    ----
        body (bytes): The body of the feedback message received from RabbitMQ.
        local_file_path (str): The local path to the file to be attached.

    Returns:
    -------
        None

    """
    logging.info("Processing feedback message.")
    data = json.loads(body)
    email = data["email"]
    ticket_number = data["ticket_number"]

    logging.info(f"Extracted email: {email}, ticket number: {ticket_number}")
    logging.info(f"Local file path: {local_file_path}")

    # Send the email with the local file path
    send_email(email, local_file_path, ticket_number)
    logging.info("Email sent successfully.")



async def consume_feedback_messages(
    rabbitmq_channel, feedback_queue, local_file_path, stop_event=None
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
        local_file_path (str): The local path to the file to be processed.
        stop_event (asyncio.Event, optional): An event object that can be used to stop consuming messages.

    Returns:
    -------
        None

    """
    logging.info("Starting to consume feedback messages.")
    while True:
        method_frame, _, body = rabbitmq_channel.basic_get(queue=feedback_queue)
        if method_frame:
            logging.info("Message received from RabbitMQ.")
            process_feedback_message(body, local_file_path)
            rabbitmq_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            logging.info("Message acknowledged.")
            if stop_event and stop_event.is_set():
                logging.info("Stop event set. Stopping message consumption.")
                break
        else:
            logging.info("No message available. Waiting for 1 second before checking again.")
            await asyncio.sleep(1)  # Wait for 1 second before checking again