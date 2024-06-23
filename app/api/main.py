
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
from api.database import create_db_and_tables, engine, get_async_session
from app_utils.file_schemas import UploadRecord
from app_utils.amqp_schemas import InferenceMessage
from fastapi import FastAPI, File, Form, UploadFile
from minio import Minio
from pydantic import ValidationError
from config import BaseConfig

from api import crud

logging.basicConfig(level=logging.INFO)

app = FastAPI()

config = BaseConfig() # environment settings
config.log_config()


minio_client = None
rabbitmq_connection = None
rabbitmq_channel = None


#################### CLIENTS ####################
def initialize_clients():
    global minio_client, rabbitmq_connection, rabbitmq_channel

    #======# STORAGE #======#
    logging.info("Initializing MinIO client...")
    minio_client = Minio(
        config.MINIO_ENDPOINT,
        access_key=config.MINIO_ACCESS_KEY,
        secret_key=config.MINIO_SECRET_KEY,
        secure=False,
    )
    logging.info("Checking if bucket exists...")
    ensure_bucket_exists(minio_client, config.MINIO_BUCKET)

    #======# FORWARDING QUEUE #======#
    logging.info("Connecting to RabbitMQ...")
    rabbitmq_connection = get_rabbit_connection(config.RABBITMQ_HOST, config.RABBITMQ_PORT)
    rabbitmq_channel = rabbitmq_connection.channel()

    logging.info(f"Declaring queue: {config.FORWARDING_QUEUE}")
    rabbitmq_channel.queue_declare(queue=config.FORWARDING_QUEUE)

    #======# FEEDBACK QUEUE #======#
    logging.info(f"Declaring queue: {config.FEEDBACK_QUEUE}")
    rabbitmq_channel.queue_declare(queue=config.FEEDBACK_QUEUE)


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
    initialize_clients()
    
    await create_db_and_tables()
    
    async for session in get_async_session():
        async with session.begin():
            await crud.populate_bird_table(session)
    
    asyncio.create_task(
        consume_feedback_messages(
            rabbitmq_channel, config.FEEDBACK_QUEUE, minio_client, config.MINIO_BUCKET
        )
    )
    
#################### ROUTES ####################
@app.get("/healthcheck")
def healthcheck() -> dict:
    """Healthcheck endpoint.

    This endpoint returns the health status of the application.

    Returns
    -------

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

    Returns
    -------
        dict: A dictionary containing the filename, success message, email, and ticket number.

    """
    file_path = "api/Turdus_merlula.wav"
    file_name = file_path.split("/")[-1]
    minio_path = f"{config.MINIO_BUCKET}/{file_name}"
    ticket_number = str(uuid.uuid4())[:6]  # Generate a 6-character ticket number

    try:
        minio_client.stat_object(config.MINIO_BUCKET, file_name)
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
            config.MINIO_BUCKET,
            file_name,
            file_content,  # Pass the file content as the data argument
        )

    message = {"minio_path": minio_path, "email": email, "ticket_number": ticket_number}

    logging.info("Publishing message to RabbitMQ...")
    publish_message(rabbitmq_channel, config.FORWARDING_QUEUE, message)

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

    Returns
    -------
        dict: A dictionary containing the filename,
        success message, email, and ticket number.

    Raises:
    ------
        HTTPException: If the uploaded file is not a .wav file,
        an error message is returned.

    """
    # Validate the input using the Pydantic model
    try:
        upload_data = UploadRecord(email=email, file=file)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.errors())

    # Generate paths
    audio_path = upload_data.get_audio_path(config.MINIO_BUCKET)
    annotation_path = upload_data.get_annotation_path(config.MINIO_BUCKET)
    spectrogram_path = upload_data.get_spectrogram_path(config.MINIO_BUCKET)

    # Read file content
    file_content = await file.read()

    # Upload file to MinIO
    try:
        minio_client.stat_object(config.MINIO_BUCKET, audio_path)
        logging.info(f"File {audio_path} already exists in MinIO.")
    except Exception as e:
        logging.error(
            f"File {audio_path} does not exist in MinIO. Uploading... Error: {e!s}"
        )
        write_file_to_minio(minio_client, config.MINIO_BUCKET, audio_path, file_content)

    ticket_number = str(uuid.uuid4())[:6]  # Generate a 6-character ticket number

    # Prepare message data
    message_data = {
        "soundfile_minio_path": audio_path,
        "email": upload_data.email,
        "ticket_number": ticket_number,
        "annotations_minio_path": annotation_path,
        "spectrogram_minio_path": spectrogram_path
    }
    message = InferenceMessage(**message_data)

    # Publish message to RabbitMQ
    logging.info("Publishing message to RabbitMQ...")
    publish_message(rabbitmq_channel, config.FORWARDING_QUEUE, message.dict())

    return {
        "filename": audio_path,
        "message": "Fichier enregistré avec succès",
        "email": upload_data.email,
        "ticket_number": message.ticket_number,
    }