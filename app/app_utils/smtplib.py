"""Email Utility Module.

This module provides a utility function for sending emails with classification results
as attachments. It fetches the JSON file containing the classification results from
MinIO, creates an email message with the JSON file as an attachment, and sends the email
using the specified SMTP server (MailHog).

"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from tempfile import NamedTemporaryFile
from app_utils.minio import fetch_file_from_minio

import logging
logging.basicConfig(level=logging.INFO)


def send_email(
    email, json_minio_path, ticket_number, minio_client, minio_bucket
) -> None:
    """
    Sends an email with the classification results as an attachment.

    The function fetches the JSON file containing the classification results from MinIO,
    creates an email message with the JSON file as an attachment, and sends the email
    using the specified SMTP server (MailHog).

    Args:
        email (str): The recipient's email address.
        json_minio_path (str): The path to the JSON file in MinIO.
        ticket_number (str): The ticket number associated with the classification request.
        minio_client (Minio): The MinIO client instance.
        minio_bucket (str): The name of the MinIO bucket where the JSON file is stored.

    Returns:
        None

    Raises:
        Exception: If an error occurs while sending the email.

    Note:
        The function uses MailHog as the SMTP server for sending emails. Make sure MailHog
        is running and accessible at the specified SMTP server and port.

        The function creates a temporary file to store the fetched JSON file locally before
        attaching it to the email. The temporary file is automatically deleted when the
        function exits.
    """
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
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.send_message(message)
        logging.info(f"\n\nEmail sent successfully to {email} for ticket #{ticket_number}\n\n")
    except Exception as e:
        logging.error(f"\n\nFailed to send email to {email} for ticket #{ticket_number}. Error: {str(e)}\n\n")