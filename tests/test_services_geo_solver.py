import pytest
from app.services.geo_solver import rssi_to_distance, DEFAULT_TX_POWER_DBM, DEFAULT_PATH_LOSS_EXPONENT

def test_rssi_to_distance_at_tx_power_equals_one_meter():
    # При RSSI == tx_power возвращается 1 метр
    dist = rssi_to_distance(rssi=DEFAULT_TX_POWER_DBM)
    assert pytest.approx(dist, rel=1e-3) == 1.0

def test_rssi_to_distance_lower_rssi_greater_distance():
    # Чем ниже RSSI, тем больше рассчитанное расстояние
    d1 = rssi_to_distance(rssi=DEFAULT_TX_POWER_DBM - 10)
    assert d1 > 1.0
