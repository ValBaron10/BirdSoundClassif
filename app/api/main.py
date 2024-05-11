import os
import uuid
import json
import asyncio
from threading import Thread
from fastapi import FastAPI, File, UploadFile
from minio import Minio

from app_utils.minio import ensure_bucket_exists, write_file_to_minio
from app_utils.rabbitmq import (
    get_rabbit_connection, 
    publish_message,
    consume_feedback_messages

)
from app_utils.smtplib import send_email

import logging
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

logging.info(f"Configuration: MINIO_ENDPOINT={MINIO_ENDPOINT}, MINIO_BUCKET={MINIO_BUCKET}")

#################### STORAGE ####################
logging.info("Initializing MinIO client...")
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False
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
    asyncio.create_task(
        consume_feedback_messages(
            rabbitmq_channel, 
            FEEDBACK_QUEUE, 
            minio_client, 
            MINIO_BUCKET
        )
    )


#################### ROUTES ####################
@app.get('/healthcheck')
def healthcheck() -> dict:
    return {"status": "ok"}

@app.get("/upload-dev")
async def upload_dev(email: str) -> dict:
    file_path = 'api/Turdus_merlula.wav'
    file_name = file_path.split('/')[-1]
    minio_path = f"{MINIO_BUCKET}/{file_name}"
    ticket_number = str(uuid.uuid4())[:6]  # Generate a 6-character ticket number

    try:
        minio_client.stat_object(MINIO_BUCKET, file_name)
        logging.info(f"File {file_name} already exists in MinIO.")
    except Exception as e:
        logging.error(f"File {file_name} does not exist in MinIO. Uploading... Error: {str(e)}")
        
        # Read the file content
        with open(file_name, 'rb') as file:
            file_content = file.read()
        
        write_file_to_minio(
            minio_client,
            MINIO_BUCKET,
            file_name,
            file_content  # Pass the file content as the data argument
        )
    
    message = {
        "minio_path": minio_path,
        "email": email,
        "ticket_number": ticket_number
    }
    
    logging.info("Publishing message to RabbitMQ...")
    publish_message(rabbitmq_channel, FORWARDING_QUEUE, message)
    
    return {"filename": 'Turdus_merlula.wav', "message": "Fichier par défaut enregistré avec succès\n", "email": email, "ticket_number": ticket_number}

"""
@app.post("/upload")
async def upload_record(file: UploadFile = File(...)):
    # Check if the file is a .wav file
    if file.content_type not in ["audio/wav"]: #TODO: implement .mp3
        return {"error": "Le fichier doit être un fichier audio .wav ou .mp3"}

    file_content = await file.read()

    # Write the file to MinIO
    write_file_to_minio(
        minio_client,
        MINIO_BUCKET,
        file.filename,
        file_content
    )

    # Publish the MinIO path to RabbitMQ
    publish_minio_path(rabbitmq_channel, FORWARDING_QUEUE, minio_path)

    return {"filename": file.filename, "message": "Fichier enregistré avec succès"}
"""