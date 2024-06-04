import logging
import os
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logging.basicConfig(level=logging.INFO)

def get_smtp_config():
    """Get SMTP configuration from environment variables."""
    smtp_server = os.getenv("SMTP_SERVER", "mailhog")
    smtp_port = int(os.getenv("SMTP_PORT", 1025))
    sender_email = os.getenv("SENDER_EMAIL", "sender@example.com")
    return smtp_server, smtp_port, sender_email

def read_file(local_file_path):
    """Read the file contents."""
    with open(local_file_path, "rb") as file:
        file_data = file.read()
    return file_data

def create_email_message(sender_email, recipient_email, ticket_number, file_data):
    """Create the email message with the file attachment."""
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = recipient_email
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

    return message

def send_email_message(smtp_server, smtp_port, message):
    """Send the email message using the SMTP server."""
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            logging.debug("SMTP server connection established")
            server.send_message(message)
            logging.debug("send_message called on SMTP server")
        logging.info(
            f"\n\nEmail sent successfully to {message['To']} for ticket #{message['Subject'].split('#')[-1]}\n\n"
        )
    except Exception as e:
        logging.error(
            f"\n\nFailed to send email to {message['To']} for ticket #{message['Subject'].split('#')[-1]}. "
            f"Error: {e!s}\n\n"
        )

def send_email(email, local_file_path, ticket_number) -> None:
    """Send an email with the classification results as an attachment."""
    smtp_server, smtp_port, sender_email = get_smtp_config()
    file_data = read_file(local_file_path)
    message = create_email_message(sender_email, email, ticket_number, file_data)
    send_email_message(smtp_server, smtp_port, message)