import pytest
from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_valid_profile():
    payload = {
        "age": 30,
        "state": "Karnataka",
        "is_student": False,
        "education_level": "Bachelor",
        "annual_family_income": 500000,
        "employment_status": "employed",
        "social_category": "General",
    }
    response = client.post("/api/profile/validate", json=payload)
    assert response.status_code == 200
    assert response.json() == payload


def test_missing_optional_fields():
    payload = {"state": "Maharashtra"}
    response = client.post("/api/profile/validate", json=payload)
    assert response.status_code == 200
    assert response.json() == payload


def test_negative_age():
    payload = {"age": -5}
    response = client.post("/api/profile/validate", json=payload)
    assert response.status_code == 422  # Pydantic validation error


def test_negative_income():
    payload = {"annual_family_income": -1000}
    response = client.post("/api/profile/validate", json=payload)
    assert response.status_code == 422

