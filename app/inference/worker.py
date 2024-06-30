"""Inference Pipeline Module.

This module implements the inference pipeline for bird sound classification.
It listens for messages from a RabbitMQ queue,
fetches the corresponding audio files from MinIO,
performs inference using a pre-trained model,
and publishes the results back to another RabbitMQ queue.

The module relies on the following dependencies:
- `app_utils.minio`: Provides utility functions for interacting with MinIO.
- `app_utils.rabbitmq`: Provides utility functions for interacting with RabbitMQ.
- `minio`: A library for interacting with MinIO object storage.
- `model_serve.model_serve`: Provides the `ModelServer` class
    for loading and running the pre-trained model.
- `src.models.bird_dict`: Provides a dictionary mapping bird species
    to their corresponding labels.

Example usage:
1. Set the required environment variables for RabbitMQ, MinIO, and model paths.
2. Run the script: `python inference_pipeline.py`
   The script will start listening for messages
   from the specified RabbitMQ queue and process them accordingly.

Note: Make sure to have the necessary dependencies installed
and the pre-trained model available before running the script.

"""

import json
import logging
import os
import io
import torch


from app_utils.minio import write_file_to_minio
from app_utils.rabbitmq import consume_messages, get_rabbit_connection, publish_message
from minio import Minio
from model_serve.model_serve import ModelServer
from pydantic import ValidationError
from src.models.bird_dict import BIRD_DICT
from app_utils.amqp_schemas import InferenceMessage, FeedbackMessage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


#################### CONFIG ####################
WEIGHTS_PATH = "models/detr_noneg_100q_bs20_r50dc5"
TEST_FILE_PATH = "inference/Turdus_merlula.wav"

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
FORWARDING_QUEUE = os.getenv("RABBITMQ_QUEUE_API2INF")
FEEDBACK_QUEUE = os.getenv("RABBITMQ_QUEUE_INF2API")
logger.info(f":[INFERENCE_PROCESS_BATCH_SIZE]: {os.getenv('INFERENCE_PROCESS_BATCH_SIZE')}")
INFERENCE_PROCESS_BATCH_SIZE = int(os.getenv("INFERENCE_PROCESS_BATCH_SIZE", "10"))


MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
MINIO_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")

#################### STORAGE ####################
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)


#################### QUEUE ####################
accumulated_messages = []

def callback(body) -> None:
    """Trigger an inference pipeline run as RabbitMQ message callback."""
    global accumulated_messages

    try:
        # Deserialize and validate the message using InferenceMessage
        message = InferenceMessage.parse_raw(body.decode())
    except ValidationError as e:
        logger.error(f"Message validation error: {e}")
        return

    logger.info(
        f"Received message from RabbitMQ: MinIO path={message.soundfile_minio_path}, "
        f"Email={message.email}, Ticket number={message.ticket_number}"
    )
    # Accumulate messages
    accumulated_messages.append(message)

    # Process batch if the batch size is reached
    if len(accumulated_messages) >= INFERENCE_PROCESS_BATCH_SIZE:
        process_batch(accumulated_messages)
        accumulated_messages = []  # Reset the list after processing

def process_batch(messages):
    """Process a batch of messages."""
    for message in messages:
        run_inference_pipeline(
            message.soundfile_minio_path,
            message.email,
            message.ticket_number,
            message.annotations_minio_path,
            message.spectrogram_minio_path
        )

#################### ML I/O  ####################
def run_inference_pipeline(minio_path, email, ticket_number, annotation_path, spectrogram_path) -> None:
    """Run inference pipeline, output classification and publish feedback message."""
    file_name = os.path.basename(minio_path)
    local_file_path = f"/tmp/{file_name}"  # Temporary local file path

    # Fetch the WAV file from MinIO and save it locally
    try:
        minio_client.fget_object(MINIO_BUCKET, minio_path, local_file_path)
        logger.info(f"WAV file downloaded from MinIO: {file_name}")
    except Exception as e:
        logger.error(f"Error downloading WAV file from MinIO: {e!s}")
        return

    inference = ModelServer(WEIGHTS_PATH, BIRD_DICT)
    inference.load()
    lines, spectrogram = inference.get_classification(local_file_path, return_spectrogram=True)
    logger.info(f"Classification output: {lines}")

    # Check if lines are empty
    if not lines:
        logger.error("No annotations found in the classification output.")
        #return

    output = io.StringIO()
    for line in lines:
        output.write(line)

    content = output.getvalue()
    logger.info(f"Annotation content: {content}")

    content_bytes = content.encode('utf-8')
    content_stream = io.BytesIO(content_bytes)
    write_file_to_minio(minio_client, MINIO_BUCKET, annotation_path, content_stream)
    
    if spectrogram:
        spectrogram_buffer = io.BytesIO()
        torch.save(spectrogram, spectrogram_buffer)
        spectrogram_buffer.seek(0)
        write_file_to_minio(minio_client, MINIO_BUCKET, spectrogram_path, spectrogram_buffer)

    # Create a FeedbackMessage instance
    feedback_message = FeedbackMessage(
        soundfile_minio_path=minio_path,
        email=email,
        ticket_number=ticket_number,
        annotations_minio_path=annotation_path,
        spectrogram_minio_path=spectrogram_path,
        classification_score=None  # Set this to the actual classification score if available
    )

    # Publish the feedback message to RabbitMQ
    publish_message(rabbitmq_channel, FEEDBACK_QUEUE, feedback_message.dict())


#################### MAIN LOOP ####################
if __name__ == "__main__":
    rabbitmq_connection = get_rabbit_connection(RABBITMQ_HOST, RABBITMQ_PORT)
    rabbitmq_channel = rabbitmq_connection.channel()
    rabbitmq_channel.queue_declare(queue=FORWARDING_QUEUE, durable=True)

    logging.info(f"Declaring queue: {FEEDBACK_QUEUE}")
    rabbitmq_channel.queue_declare(queue=FEEDBACK_QUEUE, durable=True)

    logger.info(f"Waiting for messages from queue: {FORWARDING_QUEUE}")
    consume_messages(rabbitmq_channel, FORWARDING_QUEUE, callback)
