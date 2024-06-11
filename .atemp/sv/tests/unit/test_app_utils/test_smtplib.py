import os
import pytest
import smtplib
from unittest.mock import patch, mock_open, MagicMock
from app_utils.smtplib import send_email

@pytest.fixture()
def mock_smtp():
    with patch("smtplib.SMTP") as mock:
        yield mock


def test_send_email_success(set_env_var, mock_smtp):
    email = "recipient@example.com"
    local_file_path = "/path/to/classification_results.json"
    ticket_number = "12345"

    # Mock the file read operation
    file_content = b'{"result": "classification"}'
    with patch("builtins.open", mock_open(read_data=file_content)) as mock_file:
        # Call the send_email function
        send_email(email, local_file_path, ticket_number)

        # Assert that the file was opened correctly
        mock_file.assert_called_once_with(local_file_path, "rb")

        # Assert that the SMTP server was called with the correct parameters
        mock_smtp.assert_called_once_with(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT")))

        # Get the mock SMTP instance
        smtp_instance = mock_smtp.return_value

        # Assert that the email was sent
        smtp_instance.send_message.assert_called_once()
        sent_message = smtp_instance.send_message.call_args[0][0]

        # Assert email headers and content
        assert sent_message["From"] == os.getenv("SENDER_EMAIL")
        assert sent_message["To"] == email
        assert sent_message["Subject"] == f"Classification Results - Ticket #{ticket_number}"
        assert "Please find the classification results attached." in sent_message.as_string()
        assert "classification_results.json" in sent_message.as_string()

def test_send_email_failure(set_env_var, mock_smtp):
    email = "recipient@example.com"
    local_file_path = "/path/to/classification_results.json"
    ticket_number = "12345"

    # Mock the file read operation
    file_content = b'{"result": "classification"}'
    with patch("builtins.open", mock_open(read_data=file_content)) as mock_file:
        # Simulate an SMTP exception
        smtp_instance = mock_smtp.return_value
        smtp_instance.send_message.side_effect = smtplib.SMTPException("SMTP error")

        # Call the send_email function
        with pytest.raises(smtplib.SMTPException):
            send_email(email, local_file_path, ticket_number)

        # Assert that the file was opened correctly
        mock_file.assert_called_once_with(local_file_path, "rb")

        # Assert that the SMTP server was called with the correct parameters
        mock_smtp.assert_called_once_with(os.getenv("SMTP_SERVER"), int(os.getenv("SMTP_PORT")))

        # Assert that the email sending failed
        smtp_instance.send_message.assert_called_once()