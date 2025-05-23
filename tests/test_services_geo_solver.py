import pytest
from app.services.geo_solver import rssi_to_distance, DEFAULT_TX_POWER_DBM, DEFAULT_PATH_LOSS_EXPONENT
from fastapi.testclient import TestClient
from app.main import app
import random

def test_rssi_to_distance_at_tx_power_equals_one_meter():
    # При RSSI == tx_power возвращается 1 метр
    dist = rssi_to_distance(rssi=DEFAULT_TX_POWER_DBM)
    assert pytest.approx(dist, rel=1e-3) == 1.0

def test_rssi_to_distance_lower_rssi_greater_distance():
    # Чем ниже RSSI, тем больше рассчитанное расстояние
    d1 = rssi_to_distance(rssi=DEFAULT_TX_POWER_DBM - 10)
    assert d1 > 1.0

def test_recalculate_access_point_coords_smoke(monkeypatch):
    """
    Интеграционный smoke-тест: upload_scan + пересчёт координат AP (3D/2D).
    Проверяет, что после загрузки скана координаты AP становятся валидными.
    """
    client = TestClient(app)
    scan = {
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
                "ssid": "TestWiFiA",
                "bssid": "AA:BB:CC:DD:EE:10",
                "rssi": -45,
                "frequency": 2412
            },
            {
                "ssid": "TestWiFiB",
                "bssid": "AA:BB:CC:DD:EE:11",
                "rssi": -50,
                "frequency": 2412
            },
            {
                "ssid": "TestWiFiC",
                "bssid": "AA:BB:CC:DD:EE:12",
                "rssi": -55,
                "frequency": 2412
            },
            {
                "ssid": "TestWiFiD",
                "bssid": "AA:BB:CC:DD:EE:13",
                "rssi": -60,
                "frequency": 2412
            }
        ]
    }
    response = client.post("/v1/upload", json=scan)
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "success"
    coords = data["coordinates"]
    # Проверяем, что координаты вычислены и не равны нулю
    assert coords["x"] != 0.0 or coords["y"] != 0.0
    # Проверяем, что не возникло исключений
    assert "building_id" in coords and "floor" in coords
