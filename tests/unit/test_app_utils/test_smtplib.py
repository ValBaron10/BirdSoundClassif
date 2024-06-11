import pytest
from unittest.mock import mock_open, patch, MagicMock
from app_utils.smtplib import get_smtp_config, read_file, create_email_message, send_email_message, send_email

# Fixtures
@pytest.fixture(scope="function")
def set_env_var(monkeypatch):
    env_vars = {
        "SMTP_SERVER": "mailhog",
        "SMTP_PORT": "1025",
        "SENDER_EMAIL": "sender@example.com",
    }
    for k, v in env_vars.items():
        monkeypatch.setenv(k, v)
    return

@pytest.fixture()
def smtp_mock():
    with patch("smtplib.SMTP", new_callable=MagicMock) as mock_smtp:
        yield mock_smtp

# Tests for get_smtp_config
def test_get_smtp_config(set_env_var):
    smtp_server, smtp_port, sender_email = get_smtp_config()
    assert smtp_server == "mailhog"
    assert smtp_port == 1025
    assert sender_email == "sender@example.com"

# Tests for read_file
@patch("builtins.open", new_callable=mock_open, read_data=b"file content")
def test_read_file(mock_file):
    file_data = read_file("/path/to/file")
    mock_file.assert_called_once_with("/path/to/file", "rb")
    assert file_data == b"file content"

# Tests for create_email_message
def test_create_email_message():
    sender_email = "sender@example.com"
    recipient_email = "recipient@example.com"
    ticket_number = "12345"
    file_data = b"file content"

    message = create_email_message(sender_email, recipient_email, ticket_number, file_data)

    assert message["From"] == sender_email
    assert message["To"] == recipient_email
    assert message["Subject"] == f"Classification Results - Ticket #{ticket_number}"

    parts = message.get_payload()
    assert any("Please find the classification results attached." in part.get_payload(decode=True).decode() for part in parts if part.get_content_type() == "text/plain")
    assert any("classification_results.json" in part.get_filename() for part in parts if part.get_content_type() == "application/octet-stream")

# Tests for send_email_message
def test_send_email_message(smtp_mock):
    smtp_server = "mailhog"
    smtp_port = 1025
    message = MagicMock()

    send_email_message(smtp_server, smtp_port, message)

    smtp_mock.assert_called_once_with(smtp_server, smtp_port)
    smtp_mock.return_value.__enter__().send_message.assert_called_once_with(message)

# Tests for send_email
@patch("builtins.open", new_callable=mock_open, read_data=b"file content")
@patch("app_utils.smtplib.get_smtp_config")
@patch("app_utils.smtplib.read_file")
@patch("app_utils.smtplib.create_email_message")
@patch("app_utils.smtplib.send_email_message")
def test_send_email(mock_send_email_message, mock_create_email_message, mock_read_file, mock_get_smtp_config, mock_file, set_env_var):
    email = "recipient@example.com"
    local_file_path = "/path/to/file"
    ticket_number = "12345"

    mock_get_smtp_config.return_value = ("mailhog", 1025, "sender@example.com")
    mock_read_file.return_value = b"file content"
    mock_create_email_message.return_value = MagicMock()

    send_email(email, local_file_path, ticket_number)

    mock_get_smtp_config.assert_called_once()
    mock_read_file.assert_called_once_with(local_file_path)
    mock_create_email_message.assert_called_once_with("sender@example.com", email, ticket_number, b"file content")
    mock_send_email_message.assert_called_once_with("mailhog", 1025, mock_create_email_message.return_value)