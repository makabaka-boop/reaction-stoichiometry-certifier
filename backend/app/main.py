"""FastAPI entrypoint for the exact equation-balancing workbench."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from . import balancing
from .certificate import issue_certificate
from .validation import PayloadError, validate_balance_payload, validate_verify_payload

app = FastAPI(title="化学方程式精确配平 API", version="1.0.0")


@app.exception_handler(PayloadError)
async def payload_error_handler(_request: Request, exc: PayloadError) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/balance")
async def balance_endpoint(request: Request) -> dict:
    payload = await request.json()
    compounds = validate_balance_payload(payload)
    result = balancing.balance(compounds)
    response = {"status": result["status"], "nullity": result["nullity"]}

    if result["status"] == "BALANCED":
        response["coefficients"] = result["coefficients"]
        response["elementTotals"] = result["elementTotals"]
    else:
        response["reason"] = result["reason"]

    response["certificate"] = issue_certificate(compounds, result)
    return response


@app.post("/api/verify")
async def verify_endpoint(request: Request) -> dict:
    payload: Any = await request.json()
    compounds, coefficients = validate_verify_payload(payload)
    return balancing.verify(compounds, coefficients)
