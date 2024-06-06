import os
import json
import io
from minio import Minio

from src.models.bird_dict import BIRD_DICT
from app_utils.rabbitmq import get_rabbit_connection, consume_messages, publish_message
from app_utils.minio import write_file_to_minio
from model_serve.model_serve import ModelServer


import logging

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
def callback(body) -> None:
    message = json.loads(body.decode())
    minio_path = message["minio_path"]
    email = message["email"]
    ticket_number = message["ticket_number"]

    logger.info(
        f"Received message from RabbitMQ: MinIO path={minio_path}, Email={email}, Ticket number={ticket_number}"
    )
    run_inference_pipeline(minio_path, email, ticket_number)


#################### ML I/O  ####################
def run_inference_pipeline(minio_path, email, ticket_number) -> None:
    file_name = os.path.basename(minio_path)
    local_file_path = f"/tmp/{file_name}"  # Temporary local file path

    # Fetch the WAV file from MinIO and save it locally
    try:
        minio_client.fget_object(MINIO_BUCKET, file_name, local_file_path)
        logger.info(f"WAV file downloaded from MinIO: {file_name}")
    except Exception as e:
        logger.error(f"Error downloading WAV file from MinIO: {str(e)}")
        return

    inference = ModelServer(WEIGHTS_PATH, BIRD_DICT)
    inference.load()
    lines = inference.get_classification(local_file_path)
    logger.info(f"Classification output: {lines}")

    file_name = os.path.splitext(file_name)[0] + ".txt"
    output = io.StringIO()

    for line in lines:
        output.write(line)

    content = output.getvalue()
    content_bytes = content.encode('utf-8')
    content_stream = io.BytesIO(content_bytes)

    json_data = json.dumps(lines).encode("utf-8")
    write_file_to_minio(minio_client, MINIO_BUCKET, file_name, content_stream)    

    # Publish the message containing the MinIO paths, email, and ticket number on the feedback channel
    message = {
        "wav_minio_path": f"{MINIO_BUCKET}/{file_name}",
        "json_minio_path": f"{file_name}",
        "email": email,
        "ticket_number": ticket_number,
    }
    publish_message(rabbitmq_channel, FEEDBACK_QUEUE, message)


#################### MAIN LOOP ####################
if __name__ == "__main__":
    rabbitmq_connection = get_rabbit_connection(RABBITMQ_HOST, RABBITMQ_PORT)
    rabbitmq_channel = rabbitmq_connection.channel()
    rabbitmq_channel.queue_declare(queue=FORWARDING_QUEUE)

    logging.info(f"Declaring queue: {FEEDBACK_QUEUE}")
    rabbitmq_channel.queue_declare(queue=FEEDBACK_QUEUE)

    logger.info(f"Waiting for messages from queue: {FORWARDING_QUEUE}")
    consume_messages(rabbitmq_channel, FORWARDING_QUEUE, callback)
