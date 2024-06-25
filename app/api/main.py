"""API Module.

This module implements the API endpoints 
for the bird sound classification application.
It provides endpoints for uploading audio files, 
storing them in MinIO, and publishing messages
to RabbitMQ queues for further processing. 
It also consumes feedback messages from a RabbitMQ
queue and handles them accordingly.

The module relies on the following dependencies:

app_utils.minio: Provides utility functions for interacting with MinIO.
app_utils.rabbitmq: Provides utility functions for interacting with RabbitMQ.
fastapi: A web framework for building APIs with Python.
minio: A library for interacting with MinIO object storage.
Example usage:

Set the required environment variables for RabbitMQ, MinIO, and other configurations.
Run the API server: uvicorn app.main:app --reload
Access the API endpoints using a web browser or an API client.
Available endpoints:

/healthcheck: Returns the health status of the application.
/upload-dev: Simulates the upload of a default audio file 
and publishes a message to RabbitMQ.
/upload: Allows users to upload an audio file and publishes a message to RabbitMQ.
Note: Make sure to have the necessary dependencies installed 
and the required environment variables set before running the application.

"""

import asyncio
import logging
import os
import uuid

from app_utils.minio import ensure_bucket_exists, write_file_to_minio
from app_utils.rabbitmq import (
    consume_feedback_messages,
    get_rabbit_connection,
    publish_message,
)
from fastapi import FastAPI, File, Form, UploadFile
from minio import Minio

logging.basicConfig(level=logging.INFO)

app = FastAPI()

#################### CONFIG ####################
logging.info("Loading environment variables...")
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
MINIO_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
MINIO_BUCKET = os.getenv("MINIO_BUCKET")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
FORWARDING_QUEUE = os.getenv("RABBITMQ_QUEUE_API2INF")
FEEDBACK_QUEUE = os.getenv("RABBITMQ_QUEUE_INF2API")

logging.info(
    f"Configuration: MINIO_ENDPOINT={MINIO_ENDPOINT}, MINIO_BUCKET={MINIO_BUCKET}"
)

#################### STORAGE ####################
logging.info("Initializing MinIO client...")
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)
logging.info("Checking if bucket exists...")
ensure_bucket_exists(minio_client, MINIO_BUCKET)

#################### FORWARDING QUEUE ####################
logging.info("Connecting to RabbitMQ...")
rabbitmq_connection = get_rabbit_connection(RABBITMQ_HOST, RABBITMQ_PORT)
rabbitmq_channel = rabbitmq_connection.channel()

logging.info(f"Declaring queue: {FORWARDING_QUEUE}")
rabbitmq_channel.queue_declare(queue=FORWARDING_QUEUE)

#################### FEEDBACK QUEUE ####################
logging.info(f"Declaring queue: {FEEDBACK_QUEUE}")
rabbitmq_channel.queue_declare(queue=FEEDBACK_QUEUE)


@app.on_event("startup")
async def startup_event() -> None:
    """Startup event handler.

    This function is called when the application starts up. 
    It creates a task to consume feedback messages
    from the specified RabbitMQ queue using the provided RabbitMQ channel, 
    MinIO client, and MinIO bucket.

    Returns
    -------
        None

    """
    asyncio.create_task(
        consume_feedback_messages(
            rabbitmq_channel, FEEDBACK_QUEUE, minio_client, MINIO_BUCKET
        )
    )


#################### ROUTES ####################
@app.get("/healthcheck")
def healthcheck() -> dict:
    """Healthcheck endpoint.

    This endpoint returns the health status of the application.

    Returns
    -------
        dict: {"status": "ok"}.

    """
    return {"status": "ok"}


@app.get("/upload-dev")
async def upload_dev(email: str) -> dict:
    """Development upload endpoint.

    Simulates the upload of a default file (Turdus_merlula.wav)
    to MinIO and publishes a message
    to the specified RabbitMQ queue for further processing.
    It generates a unique ticket number for the upload.

    Args:
    ----
        email (str): The email address associated with the upload.

    Returns:
    -------
        dict: A dictionary containing the filename, success message, email, and ticket number.

    """
    file_path = "api/Turdus_merlula.wav"
    file_name = file_path.split("/")[-1]
    minio_path = f"{MINIO_BUCKET}/{file_name}"
    ticket_number = str(uuid.uuid4())[:6]  # Generate a 6-character ticket number

    try:
        minio_client.stat_object(MINIO_BUCKET, file_name)
        logging.info(f"File {file_name} already exists in MinIO.")
    except Exception as e:
        logging.error(
            f"File {file_name} does not exist in MinIO. Uploading... Error: {e!s}"
        )

        # Read the file content
        with open(file_name, "rb") as file:
            file_content = file.read()

        write_file_to_minio(
            minio_client,
            MINIO_BUCKET,
            file_name,
            file_content,  # Pass the file content as the data argument
        )

    message = {"minio_path": minio_path, "email": email, "ticket_number": ticket_number}

    logging.info("Publishing message to RabbitMQ...")
    publish_message(rabbitmq_channel, FORWARDING_QUEUE, message)

    return {
        "filename": "Turdus_merlula.wav",
        "message": "Fichier par défaut enregistré avec succès\n",
        "email": email,
        "ticket_number": ticket_number,
    }


@app.post("/upload")
async def upload_record(file: UploadFile = File(...), email: str = Form(...)):
    """Upload a record endpoint.

    Allows users to upload an audio file (.wav) along with their email address.
    Checks if the file is a valid .wav file, reads the file content,
    and generates a unique ticket number.
    The file is then uploaded to MinIO, and a message is published
    to the specified RabbitMQ queue for further processing.

    Args:
    ----
        file (UploadFile): The audio file to be uploaded. It should be a .wav file.
        email (str): The email address associated with the upload.

    Returns:
    -------
        dict: A dictionary containing the filename, 
        success message, email, and ticket number.

    Raises:
    ------
        HTTPException: If the uploaded file is not a .wav file, 
        an error message is returned.

    """
    # Check if the file is a .wav file
    if file.content_type not in ["audio/wav"]:  # TODO: implement .mp3
        return {"error": "Le fichier doit être un fichier audio .wav ou .mp3"}

    file_content = await file.read()
    file_name = file.filename
    minio_path = f"{MINIO_BUCKET}/{file_name}"
    ticket_number = str(uuid.uuid4())[:6]  # Generate a 6-character ticket number

    try:
        minio_client.stat_object(MINIO_BUCKET, file_name)
        logging.info(f"File {file_name} already exists in MinIO.")
    except Exception as e:
        logging.error(
            f"File {file_name} does not exist in MinIO. Uploading... Error: {e!s}"
        )

    # write_file_to_minio(minio_client, MINIO_BUCKET, file_name, file_content)

    # message = {"minio_path": minio_path, "email": email, "ticket_number": ticket_number}

    # logging.info("Publishing message to RabbitMQ...")
    # publish_message(rabbitmq_channel, FORWARDING_QUEUE, message)

    return {
        "filename": file_name,
        "message": "Fichier enregistré avec succès",
        "email": email,
        "ticket_number": ticket_number,
    }
