import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def make_valid_scan():
    return {
        "building_id": 1,
        "floor": 1,
        "x": 10.0,
        "y": 20.0,
        "z": 1.0,
        "yaw": 0.0,
        "pitch": 0.0,
        "roll": 0.0,
        "lat": 55.7512,
        "lon": 37.6175,
        "accuracy": 5.0,
        "observations": [
            {
                "ssid": "TestWiFi",
                "bssid": "AA:BB:CC:DD:EE:01",
                "rssi": -45,
                "frequency": 2412
            },
            {
                "ssid": "TestWiFi2",
                "bssid": "AA:BB:CC:DD:EE:02",
                "rssi": -50,
                "frequency": 2412
            },
            {
                "ssid": "TestWiFi3",
                "bssid": "AA:BB:CC:DD:EE:03",
                "rssi": -55,
                "frequency": 2412
            },
            {
                "ssid": "TestWiFi4",
                "bssid": "AA:BB:CC:DD:EE:04",
                "rssi": -60,
                "frequency": 2412
            }
        ]
    }

def test_upload_invalid_payload_returns_422():
    response = client.post("/v1/upload", json={})
    assert response.status_code == 422

def test_upload_scan_success():
    scan = make_valid_scan()
    response = client.post("/v1/upload", json=scan)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    assert "coordinates" in data
    assert data["coordinates"]["building_id"] == 1
    assert data["coordinates"]["floor"] == 1

def test_upload_scan_invalid_bssid():
    scan = make_valid_scan()
    scan["observations"][0]["bssid"] = "INVALID_BSSID"
    response = client.post("/v1/upload", json=scan)
    assert response.status_code == 422
    assert "Некорректный BSSID" in response.text

def test_upload_scan_invalid_rssi():
    scan = make_valid_scan()
    scan["observations"][0]["rssi"] = -200
    response = client.post("/v1/upload", json=scan)
    assert response.status_code == 422
    assert "Некорректный RSSI" in response.text

def test_upload_scan_invalid_frequency():
    scan = make_valid_scan()
    scan["observations"][0]["frequency"] = 1000
    response = client.post("/v1/upload", json=scan)
    assert response.status_code == 422
    assert "Некорректная частота" in response.text
