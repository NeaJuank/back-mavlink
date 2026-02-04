from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_drones_endpoint():
    r = client.get("/drones")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any('name' in d for d in data)


def test_api_status():
    r = client.get("/api/status")
    assert r.status_code == 200
    j = r.json()
    assert j.get('success') is True
    assert 'data' in j
