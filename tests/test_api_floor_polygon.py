import pytest
from httpx import AsyncClient
from app.main import app
from app.db.session import async_engine
from app.db.base import Base
import asyncio

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/../app')

pytestmark = pytest.mark.asyncio

@pytest.fixture(scope="module", autouse=True)
async def prepare_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # (опционально: очистка)

@pytest.fixture
def any_polygon():
    return {
        "building_id": 1,
        "floor": 1,
        "polygon": [[0,0,0],[1,0,0],[1,1,0],[0,1,0]]
    }

async def test_crud_floor_polygon(any_polygon):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # CREATE
        resp = await ac.post("/v1/floor-polygons/", json=any_polygon)
        assert resp.status_code == 201
        data = resp.json()
        polygon_id = data["id"]
        assert data["building_id"] == any_polygon["building_id"]
        # GET
        resp = await ac.get(f"/v1/floor-polygons/{polygon_id}")
        assert resp.status_code == 200
        # LIST
        resp = await ac.get(f"/v1/floor-polygons/?building_id={any_polygon['building_id']}")
        assert resp.status_code == 200
        assert any(p["id"] == polygon_id for p in resp.json())
        # UPDATE
        new_poly = {"polygon": [[0,0,0],[2,0,0],[2,2,0],[0,2,0]]}
        resp = await ac.put(f"/v1/floor-polygons/{polygon_id}", json=new_poly)
        assert resp.status_code == 200
        assert resp.json()["polygon"] == new_poly["polygon"]
        # DELETE
        resp = await ac.delete(f"/v1/floor-polygons/{polygon_id}")
        assert resp.status_code == 204
        # GET after delete
        resp = await ac.get(f"/v1/floor-polygons/{polygon_id}")
        assert resp.status_code == 404
