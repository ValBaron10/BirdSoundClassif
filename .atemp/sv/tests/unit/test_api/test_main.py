import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, Mock, mock_open
from app.api.main import app

client = TestClient(app)


def test_upload_dev(test_app, mock_minio_client, mock_rabbitmq_channel):
    # Mock the MinIO client's stat_object method to simulate file existence
    mock_minio_client.stat_object.side_effect = Exception("File not found")
    mock_minio_client.put_object.return_value = None

    # Mock the file reading process
    with patch("builtins.open", mock_open(read_data=b"fake audio content")):
        response = test_app.get("/upload-dev?email=test@example.com")
        assert response.status_code == 200
        assert response.json()["filename"] == "Turdus_merlula.wav"
        assert response.json()["message"] == "Fichier par défaut enregistré avec succès\n"
        assert response.json()["email"] == "test@example.com"
        assert "ticket_number" in response.json()

def test_upload(test_app, mock_minio_client, mock_rabbitmq_channel):
    # Mock the MinIO client's stat_object method to simulate file existence
    mock_minio_client.stat_object.side_effect = Exception("File not found")
    mock_minio_client.put_object.return_value = None

    file_content = b"fake audio content"
    files = {"file": ("test.wav", file_content, "audio/wav")}
    data = {"email": "test@example.com"}

    response = test_app.post("/upload", files=files, data=data)
    assert response.status_code == 200
    assert response.json()["filename"] == "test.wav"
    assert response.json()["message"] == "Fichier enregistré avec succès"
    assert response.json()["email"] == "test@example.com"
    assert "ticket_number" in response.json()

def test_upload_invalid_file(test_app):
    file_content = b"fake audio content"
    files = {"file": ("test.txt", file_content, "text/plain")}
    data = {"email": "test@example.com"}

    response = test_app.post("/upload", files=files, data=data)
    assert response.status_code == 200
    assert response.json() == {"error": "Le fichier doit être un fichier audio .wav ou .mp3"}