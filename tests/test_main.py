"""
test_main.py
============
Integration & Unit Test Suite for FastAPI Repair or Replace Advisor Backend.

Verifies:
1. Health check & database connection
2. POST /api/diagnose (Age assessment, ranked causes, cost bands, DIY difficulty, case auto-creation)
3. POST /api/quote-check (Fair price, inflated price, unusually low price flags)
4. POST /api/verdict (Cost engine integration, verdict, sensitivity confidence, flip point)
5. POST /api/photo (Multipart image upload, rating plate metadata extraction)
6. GET  /api/cases/{id} (Case retrieval by ID, 404 on unknown ID)
"""

import io
import json
import os
import sys
import pytest

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_tests_dir)
_backend_dir = os.path.join(_root_dir, "backend")
for _p in [_root_dir, _backend_dir, _tests_dir]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from fastapi.testclient import TestClient
    try:
        from backend.main import app
    except ImportError:
        from main import app
    _FASTAPI_TEST_READY = True
except ImportError:
    _FASTAPI_TEST_READY = False


@pytest.fixture(scope="module")
def client():
    """Provides a TestClient context manager triggering lifespan events."""
    if not _FASTAPI_TEST_READY:
        pytest.skip("FastAPI / TestClient not installed in environment")
    with TestClient(app) as test_client:
        yield test_client


# ============================================================================
# 1. HEALTH & REFERENCE DATA TESTS
# ============================================================================

def test_health_check(client):
    """Verifies service health check and database query execution."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"


def test_serve_ui_root(client):
    """Verifies root endpoint serves HTML UI or API fallback."""
    resp = client.get("/")
    assert resp.status_code == 200
    assert "html" in resp.headers.get("content-type", "").lower() or "application/json" in resp.headers.get("content-type", "").lower()


def test_list_appliance_references(client):
    """Verifies that lifespan and startup seeded appliance reference data."""
    resp = client.get("/api/reference/appliances")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 4
    types = [i["appliance_type"] for i in items]
    assert "Washing Machine" in types
    assert "Air Conditioner" in types


def test_list_part_price_bands(client):
    """Verifies that startup seeded part benchmark price bands."""
    resp = client.get("/api/reference/price-bands")
    assert resp.status_code == 200
    bands = resp.json()
    assert len(bands) >= 5
    part_names = [b["part_category"] for b in bands]
    assert any("Drain Pump" in p for p in part_names)


# ============================================================================
# 2. POST /api/diagnose TESTS
# ============================================================================

def test_diagnose_endpoint(client):
    """Tests diagnostic triage, age assessment, cost bands, and case creation."""
    payload = {
        "appliance_type": "Washing Machine",
        "brand": "IFB",
        "age": 3.5,
        "symptom_text": "Machine is displaying dE error code and beeping continuously",
        "model": "Senator Smart Touch",
        "error_code": "dE",
    }
    resp = client.post("/api/diagnose", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["brand"] == "IFB"
    assert data["appliance_type"] == "Washing Machine"
    assert "Early Lifecycle" in data["age_assessment"] or "Mid Lifecycle" in data["age_assessment"]
    assert len(data["ranked_causes"]) >= 1

    # Verify ranked cause structure
    first_cause = data["ranked_causes"][0]
    assert "cost_band" in first_cause
    assert first_cause["cost_band"]["low"] > 0
    assert first_cause["cost_band"]["high"] >= first_cause["cost_band"]["low"]
    assert first_cause["diy_difficulty"] in ("Easy DIY", "Moderate DIY", "Technician Required", "Specialist/Hazard")
    assert "case_id" in data
    assert data["case_id"].startswith("case_")


# ============================================================================
# 3. POST /api/quote-check TESTS
# ============================================================================

def test_quote_check_fair_price(client):
    """Verifies fair price quote within threshold."""
    payload = {
        "appliance_category": "Washing Machine",
        "part_category": "Drain Pump",
        "quoted_part_price": 1600.0,  # Fair price within [1100, 2200]
        "quoted_labor_price": 400.0,
    }
    resp = client.post("/api/quote-check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["part_status"] == "fair"
    assert data["labor_status"] == "fair"
    assert data["overall_status"] == "reasonable"


def test_quote_check_inflated_price(client):
    """Verifies inflated quote detection and warning flags."""
    payload = {
        "appliance_category": "Washing Machine",
        "part_category": "Drain Pump",
        "quoted_part_price": 3800.0,  # High above high threshold 2200
        "quoted_labor_price": 1200.0, # High labor above benchmark 400
    }
    resp = client.post("/api/quote-check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["part_status"] == "inflated"
    assert data["labor_status"] == "inflated"
    assert data["overall_status"] == "inflated"
    assert any("ABOVE the benchmark" in n for n in data["advisory_notes"])


def test_quote_check_unusually_low_price(client):
    """Verifies flag for suspicious low-cost part quotes."""
    payload = {
        "appliance_category": "Washing Machine",
        "part_category": "Drain Pump",
        "quoted_part_price": 300.0,  # Below 1100 * 0.65
    }
    resp = client.post("/api/quote-check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["part_status"] == "unusually_low"


# ============================================================================
# 4. POST /api/verdict TESTS
# ============================================================================

def test_verdict_endpoint(client):
    """Tests deterministic cost engine calculation via API."""
    payload = {
        "Q": 350.0,
        "tr": 4.0,
        "tn": 6.0,
        "v": 25.0,
        "p": 0.20,
        "E_old": 180.0,
        "E_new": 90.0,
        "L_r": 2.5,
        "L_n": 10.0,
        "P": 900.0,
        "D": 80.0,
        "S": 40.0,
    }
    resp = client.post("/api/verdict", json=payload)
    assert resp.status_code == 200
    data = resp.json()

    assert data["verdict"] in ("Repair", "Replace")
    assert data["confidence"] in ("firm", "close")
    assert "annual_repair_cost" in data
    assert "annual_replace_cost" in data
    assert "flip_assumption" in data
    assert "To flip the verdict" in data["flip_assumption"]
    assert "breakdown" in data


# ============================================================================
# 5. POST /api/photo TESTS
# ============================================================================

def test_photo_extraction_endpoint(client):
    """Tests multipart rating plate sticker photo upload and extraction."""
    # Create fake image bytes containing text markers
    fake_image = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00MODEL: 183V VECTRA VOLTAS 230V 50HZ SERIAL: VOL-992834\xff\xd9"
    files = {"file": ("sticker.jpg", io.BytesIO(fake_image), "image/jpeg")}
    data = {"hint_brand": "VOLTAS", "hint_type": "Air Conditioner"}

    resp = client.post("/api/photo", files=files, data=data)
    assert resp.status_code == 200
    res_data = resp.json()

    assert res_data["brand"] == "VOLTAS"
    assert "183V" in res_data["model_number"] or "VECTRA" in res_data["model_number"]
    assert "electrical_specs" in res_data
    assert res_data["confidence_score"] > 0.70


# ============================================================================
# 6. GET /api/cases/{id} TESTS
# ============================================================================

def test_case_lifecycle_and_retrieval(client):
    """Full lifecycle: create via diagnose -> retrieve by ID -> update via verdict."""
    # 1. Create Case
    diag_resp = client.post(
        "/api/diagnose",
        json={
            "appliance_type": "Refrigerator",
            "brand": "Godrej",
            "age": 2.0,
            "symptom_text": "Ticking click sound from compressor every 2 minutes",
        },
    )
    assert diag_resp.status_code == 200
    case_id = diag_resp.json()["case_id"]

    # 2. Retrieve Case by ID
    get_resp = client.get(f"/api/cases/{case_id}")
    assert get_resp.status_code == 200
    case_data = get_resp.json()
    assert case_data["id"] == case_id
    assert case_data["user_input_snapshot"]["brand"] == "Godrej"
    assert case_data["returned_diagnosis"] is not None

    # 3. Update Case with Verdict
    verdict_resp = client.post(
        "/api/verdict",
        json={
            "case_id": case_id,
            "Q": 180.0,
            "tr": 2.0, "tn": 4.0, "v": 20.0, "p": 0.10,
            "E_old": 150.0, "E_new": 100.0,
            "L_r": 3.0, "L_n": 10.0,
            "P": 950.0, "D": 50.0, "S": 30.0,
        },
    )
    assert verdict_resp.status_code == 200

    # 4. Re-retrieve Case and verify updated verdict & cost fields
    re_get = client.get(f"/api/cases/{case_id}")
    assert re_get.status_code == 200
    updated_data = re_get.json()
    assert updated_data["cost_parameters"] is not None
    assert updated_data["final_verdict"] is not None
    assert updated_data["final_verdict"]["verdict"] in ("Repair", "Replace")


def test_get_nonexistent_case_returns_404(client):
    """Non-existent case ID must return 404 Not Found."""
    resp = client.get("/api/cases/nonexistent_case_999999")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()

