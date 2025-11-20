from fastapi.testclient import TestClient
from main import app
client = TestClient(app)

def test_root():
    r = client.get("/")
    assert r.status_code == 200

def test_upload_without_file():
    r = client.post("/upload-dataset")
    assert r.status_code == 422  # missing file
