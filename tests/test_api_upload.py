import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_upload_invalid_payload_returns_422():
    response = client.post("/v1/upload", json={})
    assert response.status_code == 422
