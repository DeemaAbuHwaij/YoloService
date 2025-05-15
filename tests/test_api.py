from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

def test_predict_success():
    with open("tests/sample.jpg", "rb") as f:
        response = client.post("/predict", files={"file": f})
    assert response.status_code == 200
    assert "labels" in response.json()

def test_predict_failure():
    # Send invalid content
    response = client.post("/predict", data={"file": "not-a-file"})
    assert response.status_code in [400, 422]

