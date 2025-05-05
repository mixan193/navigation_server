import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_map_bad_id_returns_422():
    response = client.get("/v1/map/not-an-int")
    assert response.status_code == 422
