import time
import json
import pika
import asyncio
import threading


from app_utils.smtplib import send_email

import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Global variable to manage RabbitMQ connection
rabbit_connection = None


def connect_to_rabbitmq(host, port, max_retries=5, retry_delay=5) -> pika.BlockingConnection:
    """
    Connects to RabbitMQ with automatic retries.

    Args:
        host (str): The hostname or IP address of the RabbitMQ server.
        port (int): The port number of the RabbitMQ server.
        max_retries (int, optional): The maximum number of connection retries.
        retry_delay (int, optional): The delay in seconds between each retry attempt.

    Returns:
        pika.BlockingConnection: The established connection to RabbitMQ.

    Raises:
        Exception: If the connection to RabbitMQ fails after the specified number of retries.
    """
    global rabbit_connection
    retry_count = 0

    while retry_count < max_retries:
        logging.info(f"Attempting to connect to RabbitMQ (Attempt {retry_count + 1}/{max_retries})")
        try:
            rabbit_connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=host, port=port)
            )
            logging.info("Successfully connected to RabbitMQ")
            return rabbit_connection
        except pika.exceptions.AMQPConnectionError as e:
            logging.error(f"Error connecting to RabbitMQ: {str(e)}. Retrying in {retry_delay} seconds...")
            retry_count += 1
            time.sleep(retry_delay)
            if retry_count == max_retries:
                logging.critical("Failed to connect to RabbitMQ after multiple retries.")
                raise Exception("Failed to connect to RabbitMQ after multiple retries.")


def get_rabbit_connection(host, port) -> pika.BlockingConnection:
    """
    Gets the current RabbitMQ connection or establishes a new one if necessary.

    Returns:
        pika.BlockingConnection: The active RabbitMQ connection.
    """
    global rabbit_connection
    logging.info("Checking RabbitMQ connection")
    if rabbit_connection is None or rabbit_connection.is_closed:
        logging.info("RabbitMQ connection is None or closed. Establishing a new connection.")
        connect_to_rabbitmq(host, port)
        logging.info("RabbitMQ connection established.")
    else:
        logging.info("RabbitMQ connection is active.")
    return rabbit_connection


def publish_minio_path(channel, queue_name, minio_path) -> None:
    """
    Publishes a MinIO path to a specified RabbitMQ queue.

    Args:
        channel: The active channel of the RabbitMQ connection.
        queue_name (str): The name of the queue where the message will be published.
        minio_path (str): The MinIO path to be published.

    Returns:
        None
    """
    logging.info(f"Preparing to publish MinIO path to queue: {queue_name}")
    try:
        channel.basic_publish(exchange="", routing_key=queue_name, body=minio_path)
        logging.info(f"Published MinIO path: {minio_path}")
    except Exception as e:
        logging.error(f"Failed to publish MinIO path: {str(e)}")


def publish_message(channel, queue_name, message) -> None:
    """
    Publishes a message to a specified RabbitMQ queue.

    Args:
        channel: The active channel of the RabbitMQ connection.
        queue_name (str): The name of the queue where the message will be published.
        message (dict): The message to be published, containing the MinIO path, email, and ticket number.

    Returns:
        None
    """
    logging.info(f"Preparing to publish message to queue: {queue_name}")
    try:
        channel.basic_publish(exchange="", routing_key=queue_name, body=json.dumps(message))
        logging.info(f"Published message: {message}")
    except Exception as e:
        logging.error(f"Failed to publish message: {str(e)}")
        

def consume_messages(channel, queue_name, callback) -> None:
    """
    Consumes messages from a specified RabbitMQ queue and invokes a callback function for each message.

    Args:
        channel: The active channel of the RabbitMQ connection.
        queue_name (str): The name of the queue to consume messages from.
        callback (function): The callback function to be invoked for each received message.
                             The function should accept a single argument, which is the message body.

    Returns:
        None
    """
    def on_message(ch, method, properties, body):
        """
        Callback function invoked for each received message.

        Args:
            ch: The channel object.
            method: The delivery method.
            properties: The message properties.
            body: The message body.
        """
        callback(body)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_consume(queue=queue_name, on_message_callback=on_message)
    channel.start_consuming()
    
    
def process_feedback_message(body, minio_client, minio_bucket):
    data = json.loads(body)
    email = data["email"]
    json_minio_path = data["json_minio_path"]
    ticket_number = data["ticket_number"]
    
    json_file_path = f"{json_minio_path}"
    send_email(email, json_file_path, ticket_number, minio_client, minio_bucket)


async def consume_feedback_messages(rabbitmq_channel, feedback_queue, minio_client, minio_bucket):
    while True:
        method_frame, _, body = rabbitmq_channel.basic_get(queue=feedback_queue)
        if method_frame:
            process_feedback_message(body, minio_client, minio_bucket)
            rabbitmq_channel.basic_ack(delivery_tag=method_frame.delivery_tag)
        else:
            await asyncio.sleep(1)  # Wait for 1 second before checking again



#########################################################
###################### REFACTORING ######################
#########################################################
# TODO replace function calls with this class in main.py
# TODO docstrings, retrun hints
 
class RabbitMQClient:
    def __init__(self, host, port, max_retries=5, retry_delay=5):
        self.host = host
        self.port = port
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.connection = None
        self.channel = None

    def connect(self):
        retry_count = 0

        while retry_count < self.max_retries:
            logging.info(f"Attempting to connect to RabbitMQ (Attempt {retry_count + 1}/{self.max_retries})")
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=self.host, port=self.port)
                )
                logging.info("Successfully connected to RabbitMQ")
                self.channel = self.connection.channel()
                return
            except pika.exceptions.AMQPConnectionError as e:
                logging.error(f"Error connecting to RabbitMQ: {str(e)}. Retrying in {self.retry_delay} seconds...")
                retry_count += 1
                time.sleep(self.retry_delay)
                if retry_count == self.max_retries:
                    logging.critical("Failed to connect to RabbitMQ after multiple retries.")
                    raise Exception("Failed to connect to RabbitMQ after multiple retries.")

    def get_connection(self):
        logging.info("Checking RabbitMQ connection")
        if self.connection is None or self.connection.is_closed:
            logging.info("RabbitMQ connection is None or closed. Establishing a new connection.")
            self.connect()
            logging.info("RabbitMQ connection established.")
        else:
            logging.info("RabbitMQ connection is active.")
        return self.connection

    def publish_minio_path(self, queue_name, minio_path):
        logging.info(f"Preparing to publish MinIO path to queue: {queue_name}")
        try:
            self.channel.basic_publish(exchange="", routing_key=queue_name, body=minio_path)
            logging.info(f"Published MinIO path: {minio_path}")
        except Exception as e:
            logging.error(f"Failed to publish MinIO path: {str(e)}")

    def publish_message(self, queue_name, message):
        logging.info(f"Preparing to publish message to queue: {queue_name}")
        try:
            self.channel.basic_publish(exchange="", routing_key=queue_name, body=json.dumps(message))
            logging.info(f"Published message: {message}")
        except Exception as e:
            logging.error(f"Failed to publish message: {str(e)}")

    def consume_messages(self, queue_name, callback):
        def on_message(ch, method, properties, body):
            callback(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        self.channel.basic_consume(queue=queue_name, on_message_callback=on_message)
        self.channel.start_consuming()

    def process_feedback_message(self, message):
        data = json.loads(message.decode("utf-8"))
        email = data["email"]
        ticket_number = data["ticket_number"]
        json_data = json.dumps(data, indent=4)  # Format the JSON data for readability

        send_email(email, json_data, ticket_number)

    async def consume_feedback_messages(self, feedback_queue):
        while True:
            method_frame, _, body = self.channel.basic_get(queue=feedback_queue)
            if method_frame:
                self.process_feedback_message(body)
                self.channel.basic_ack(delivery_tag=method_frame.delivery_tag)
            else:
                await asyncio.sleep(1)  # Wait for 1 second before checking again
