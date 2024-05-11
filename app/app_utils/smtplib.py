import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from tempfile import NamedTemporaryFile
from app_utils.minio import fetch_file_from_minio

import logging

logging.basicConfig(level=logging.INFO)


def send_email(email, json_minio_path, ticket_number, minio_client, minio_bucket) -> None:
    # SMTP configuration for MailHog
    smtp_server = "mailhog"
    smtp_port = 1025
    sender_email = "sender@example.com"

    # Create a temporary file to store the fetched JSON file
    with NamedTemporaryFile(delete=False) as temp_file:
        local_file_path = temp_file.name

        # Fetch the JSON file from MinIO and save it locally
        success = fetch_file_from_minio(
            minio_client, minio_bucket, json_minio_path, local_file_path
        )

        if not success:
            logging.error(
                f"Failed to fetch JSON file '{json_minio_path}' from MinIO. Skipping email sending."
            )
            return

        # Read the JSON file contents
        with open(local_file_path, "rb") as file:
            json_data = file.read()

    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = f"Classification Results - Ticket #{ticket_number}"

    # Attach the email body
    body = f"Please find the classification results attached.\n\nTicket Number: {ticket_number}"
    message.attach(MIMEText(body, "plain"))

    # Attach the JSON file
    json_file = MIMEApplication(json_data, _subtype="json")
    json_file.add_header(
        "Content-Disposition", "attachment", filename="classification_results.json"
    )
    message.attach(json_file)

    # Send the email
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.send_message(message)
