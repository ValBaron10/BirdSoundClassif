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
            logging.info(
                f"Attempting to connect to RabbitMQ (Attempt {retry_count + 1}/{self.max_retries})"
            )
            try:
                self.connection = pika.BlockingConnection(
                    pika.ConnectionParameters(host=self.host, port=self.port)
                )
                logging.info("Successfully connected to RabbitMQ")
                self.channel = self.connection.channel()
                return
            except pika.exceptions.AMQPConnectionError as e:
                logging.error(
                    f"Error connecting to RabbitMQ: {e!s}. Retrying in {self.retry_delay} seconds..."
                )
                retry_count += 1
                time.sleep(self.retry_delay)
                if retry_count == self.max_retries:
                    logging.critical(
                        "Failed to connect to RabbitMQ after multiple retries."
                    )
                    raise Exception(
                        "Failed to connect to RabbitMQ after multiple retries."
                    )

    def get_connection(self):
        logging.info("Checking RabbitMQ connection")
        if self.connection is None or self.connection.is_closed:
            logging.info(
                "RabbitMQ connection is None or closed. Establishing a new connection."
            )
            self.connect()
            logging.info("RabbitMQ connection established.")
        else:
            logging.info("RabbitMQ connection is active.")
        return self.connection

    def publish_minio_path(self, queue_name, minio_path):
        logging.info(f"Preparing to publish MinIO path to queue: {queue_name}")
        try:
            self.channel.basic_publish(
                exchange="", routing_key=queue_name, body=minio_path
            )
            logging.info(f"Published MinIO path: {minio_path}")
        except Exception as e:
            logging.error(f"Failed to publish MinIO path: {e!s}")

    def publish_message(self, queue_name, message):
        logging.info(f"Preparing to publish message to queue: {queue_name}")
        try:
            self.channel.basic_publish(
                exchange="", routing_key=queue_name, body=json.dumps(message)
            )
            logging.info(f"Published message: {message}")
        except Exception as e:
            logging.error(f"Failed to publish message: {e!s}")

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


def publish_minio_path(channel, queue_name, minio_path) -> None:
    """Publish a MinIO path to a specified RabbitMQ queue.

    Args:
    ----
        channel: The active channel of the RabbitMQ connection.
        queue_name (str): The name of the queue where the message will be published.
        minio_path (str): The MinIO path to be published.

    Returns:
    -------
        None

    """
    logging.info(f"Preparing to publish MinIO path to queue: {queue_name}")
    try:
        channel.basic_publish(exchange="", routing_key=queue_name, body=minio_path)
        logging.info(f"Published MinIO path: {minio_path}")
    except Exception as e:
        logging.error(f"Failed to publish MinIO path: {e!s}")