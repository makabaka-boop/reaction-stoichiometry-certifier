"""End-to-end FastAPI tests covering validation, certificates and /verify."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

H2_O2 = {
    "compounds": [
        {"id": "H2", "role": "REACTANT", "composition": {"H": 2}},
        {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
        {"id": "H2O", "role": "PRODUCT", "composition": {"H": 2, "O": 1}},
    ]
}


def test_health():
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_balance_success_returns_certificate():
    response = client.post("/api/balance", json=H2_O2)
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "BALANCED"
    assert body["nullity"] == 1
    coefficients = {item["id"]: item["coefficient"] for item in body["coefficients"]}
    assert coefficients == {"H2": 2, "O2": 1, "H2O": 2}
    assert body["elementTotals"]["H"] == {"reactant": 4, "product": 4}
    assert body["elementTotals"]["O"] == {"reactant": 2, "product": 2}

    certificate = body["certificate"]
    assert certificate["status"] == "BALANCED"
    assert certificate["certificateId"].startswith("CERT-")
    assert len(certificate["inputFingerprint"]) == 16


def test_certificate_fingerprint_changes_with_any_edit():
    first = client.post("/api/balance", json=H2_O2).json()["certificate"]

    edited = {
        "compounds": [
            {"id": "H2", "role": "REACTANT", "composition": {"H": 3}},
            {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
            {"id": "H2O", "role": "PRODUCT", "composition": {"H": 2, "O": 1}},
        ]
    }
    second = client.post("/api/balance", json=edited).json()["certificate"]
    assert first["inputFingerprint"] != second["inputFingerprint"]


def test_reordering_compounds_keeps_fingerprint_canonical():
    # Canonical hash is content based; key order inside composition does not
    # change it, while list order (which assigns columns) is retained.
    reordered_keys = {
        "compounds": [
            {"composition": {"H": 2}, "role": "REACTANT", "id": "H2"},
            {"composition": {"O": 2}, "role": "REACTANT", "id": "O2"},
            {"composition": {"O": 1, "H": 2}, "role": "PRODUCT", "id": "H2O"},
        ]
    }
    first = client.post("/api/balance", json=H2_O2).json()["certificate"]
    second = client.post("/api/balance", json=reordered_keys).json()["certificate"]
    assert first["inputFingerprint"] == second["inputFingerprint"]


@pytest.mark.parametrize(
    "payload,code",
    [
        ({"compounds": [{"id": "A", "role": "REACTANT", "composition": {"H": 1}}]},
         "INVALID_COMPOUND_COUNT"),
        ({"compounds": "nope"}, "INVALID_TYPE"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {"H": 1}},
            {"id": "A", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "DUPLICATE_ID"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {"H": 1}},
            {"id": "B", "role": "PRODUCT", "composition": {"Xx": 1}},
        ]}, "INVALID_ELEMENT"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "EMPTY_COMPOSITION"),
        ({"compounds": [
            {"id": "A", "role": "LEFT", "composition": {"H": 1}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "INVALID_ROLE"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {"H": 0}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "INVALID_ELEMENT_COUNT"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {"H": -1}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "INVALID_ELEMENT_COUNT"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {"H": True}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "INVALID_ELEMENT_COUNT"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {"H": 1.5}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "INVALID_ELEMENT_COUNT"),
        ({"compounds": [
            {"id": "", "role": "REACTANT", "composition": {"H": 1}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "INVALID_ID"),
        ({"compounds": [
            {"id": "氢", "role": "REACTANT", "composition": {"H": 1}},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "INVALID_ID"),
        ({"compounds": [
            {"id": "A", "role": "REACTANT", "composition": {"H": 1}, "note": "x"},
            {"id": "B", "role": "PRODUCT", "composition": {"O": 1}},
        ]}, "UNKNOWN_FIELD"),
    ],
)
def test_validation_rejects_whole_document(payload, code):
    response = client.post("/api/balance", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == code


def test_too_many_elements_rejected():
    symbols = ["H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne",
               "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K", "Ca", "Sc"]
    payload = {
        "compounds": [
            {"id": "A", "role": "REACTANT",
             "composition": {symbol: 1 for symbol in symbols[:11]}},
            {"id": "B", "role": "PRODUCT",
             "composition": {symbol: 1 for symbol in symbols[11:]}},
        ]
    }
    response = client.post("/api/balance", json=payload)
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "TOO_MANY_ELEMENTS"


def test_verify_accepts_certified_coefficients():
    response = client.post("/api/verify", json={**H2_O2, "coefficients": {
        "H2": 2, "O2": 1, "H2O": 2,
    }})
    assert response.status_code == 200
    body = response.json()
    assert body["balanced"] is True
    assert body["primitive"] is True
    assert body["allPositive"] is True
    assert body["gcd"] == 1
    assert body["reasons"] == []
    for check in body["elementChecks"].values():
        assert check["balanced"] is True


def test_verify_flags_non_conservation_per_element():
    response = client.post("/api/verify", json={**H2_O2, "coefficients": {
        "H2": 1, "O2": 1, "H2O": 1,
    }})
    body = response.json()
    assert body["balanced"] is False
    assert body["elementChecks"]["H"]["balanced"] is True
    assert body["elementChecks"]["H"]["reactant"] == 2
    assert body["elementChecks"]["H"]["product"] == 2
    assert body["elementChecks"]["O"]["balanced"] is False
    assert body["elementChecks"]["O"]["reactant"] == 2
    assert body["elementChecks"]["O"]["product"] == 1
    assert "ELEMENT_NOT_CONSERVED" in body["reasons"]


def test_verify_flags_non_primitive_even_when_conserved():
    # 4, 2, 4 conserves every element but has overall gcd 2.
    response = client.post("/api/verify", json={**H2_O2, "coefficients": {
        "H2": 4, "O2": 2, "H2O": 4,
    }})
    body = response.json()
    assert body["balanced"] is True
    assert body["primitive"] is False
    assert body["gcd"] == 2
    assert any(reason.startswith("NOT_PRIMITIVE_GCD_") for reason in body["reasons"])


def test_verify_flags_non_positive():
    response = client.post("/api/verify", json={**H2_O2, "coefficients": {
        "H2": 0, "O2": 0, "H2O": 0,
    }})
    body = response.json()
    assert body["balanced"] is False
    assert body["primitive"] is False
    assert body["allPositive"] is False
    assert "NON_POSITIVE_COEFFICIENT" in body["reasons"]


def test_verify_rejects_missing_and_unknown_coefficients():
    response = client.post("/api/verify", json={**H2_O2, "coefficients": {
        "H2": 2, "O2": 1,
    }})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MISSING_COEFFICIENT"

    response = client.post("/api/verify", json={**H2_O2, "coefficients": {
        "H2": 2, "O2": 1, "H2O": 2, "X9": 1,
    }})
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNKNOWN_COEFFICIENT"
