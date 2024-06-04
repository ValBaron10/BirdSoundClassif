import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)

def send_email(email, local_file_path, ticket_number) -> None:
    """Send an email with the classification results as an attachment.

    The function fetches the JSON file containing the classification results from MinIO,
    creates an email message with the JSON file as an attachment, and sends the email
    using the specified SMTP server (MailHog).

    Args:
    ----
        email (str): The recipient's email address.
        local_file_path (str): The local path to the file to be attached.
        ticket_number (str): The ticket number associated with the classification request.

    Returns:
    -------
        None

    Raises:
    ------
        Exception: If an error occurs while sending the email.

    Note:
    ----
        The function uses MailHog as the SMTP server for sending emails. Make sure MailHog
        is running and accessible at the specified SMTP server and port.

    """
    # SMTP configuration from environment variables
    smtp_server = os.getenv("SMTP_SERVER", "mailhog")
    smtp_port = int(os.getenv("SMTP_PORT", 1025))
    sender_email = os.getenv("SENDER_EMAIL", "sender@example.com")

    logging.debug(f"SMTP server: {smtp_server}, port: {smtp_port}, sender: {sender_email}")

    # Read the file contents
    with open(local_file_path, "rb") as file:
        file_data = file.read()
        logging.debug(f"File {local_file_path} read successfully")

    # Create the email message
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = email
    message["Subject"] = f"Classification Results - Ticket #{ticket_number}"

    # Attach the email body
    body = f"Please find the classification results attached.\n\nTicket Number: {ticket_number}"
    message.attach(MIMEText(body, "plain"))

    # Attach the file
    file_attachment = MIMEApplication(file_data, _subtype="octet-stream")
    file_attachment.add_header(
        "Content-Disposition", "attachment", filename="classification_results.json"
    )
    message.attach(file_attachment)

    logging.debug("Email message created successfully")

    # Send the email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logging.debug("SMTP server connection established")
            server.send_message(message)
            logging.debug("send_message called on SMTP server")
        logging.info(
            f"\n\nEmail sent successfully to {email} for ticket #{ticket_number}\n\n"
        )
    except Exception as e:
        logging.error(
            f"\n\nFailed to send email to {email} for ticket #{ticket_number}. "
            f"Error: {e!s}\n\n"
        )