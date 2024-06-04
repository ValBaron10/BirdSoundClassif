import pytest
from unittest.mock import mock_open, patch
from app_utils.smtplib import send_email


@patch("builtins.open", new_callable=mock_open, read_data=b"file content")
def test_send_email(mock_file, smtpd, set_env_var):
    email = "recipient@example.com"
    local_file_path = "/path/to/file"
    ticket_number = "12345"

    send_email(email, local_file_path, ticket_number)

    # Check if the file was opened correctly
    mock_file.assert_called_once_with(local_file_path, "rb")

    # Verify that the email was sent
    assert len(smtpd.messages) == 1
    sent_message = smtpd.messages[0]

    # Verify the sender, recipient, and subject
    assert sent_message["From"] == "sender@example.com"
    assert sent_message["To"] == email
    assert sent_message["Subject"] == f"Classification Results - Ticket #{ticket_number}"

    # Extract and verify the email body and attachment
    parts = sent_message.get_payload()
    assert any("Please find the classification results attached." in part.get_payload(decode=True).decode() for part in parts if part.get_content_type() == "text/plain")
    assert any("classification_results.json" in part.get_filename() for part in parts if part.get_content_type() == "application/octet-stream")