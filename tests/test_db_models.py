import pytest
from app.db.base import Base

def test_models_metadata_registered():
    tables = Base.metadata.tables.keys()
    expected = {"building", "access_point", "wifi_snapshot", "wifi_obs", "floor_polygon"}
    assert expected.issubset(set(tables))
