"""Whole-document payload validation.

The specification rejects the entire submission on any malformed field:
unknown fields, duplicate IDs, illegal element symbols or empty composition
all produce a 400 with a machine-readable error code.  Booleans are not
accepted as integers (``True`` is not a positive element count).
"""

from __future__ import annotations

import re
from typing import Any, Tuple

from .elements import ELEMENT_SYMBOLS

ID_PATTERN = re.compile(r"^[\x20-\x7E]+$")
ROLES = frozenset({"REACTANT", "PRODUCT"})
COMPOUND_FIELDS = frozenset({"id", "role", "composition"})
TOP_FIELDS = frozenset({"compounds"})
MIN_COMPOUNDS = 2
MAX_COMPOUNDS = 12
MAX_ELEMENTS = 20


class PayloadError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _reject(code: str, message: str) -> None:
    raise PayloadError(code, message)


def _is_positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def validate_balance_payload(payload: Any) -> list:
    """Validate a /balance request body and return the normalised compounds."""
    if not isinstance(payload, dict):
        _reject("INVALID_JSON", "请求体必须是 JSON 对象")

    unknown = set(payload) - TOP_FIELDS
    if unknown:
        _reject("UNKNOWN_FIELD", f"存在未知字段: {sorted(unknown)}")
    if "compounds" not in payload:
        _reject("MISSING_FIELD", "缺少 compounds 字段")

    compounds = payload["compounds"]
    if not isinstance(compounds, list):
        _reject("INVALID_TYPE", "compounds 必须是数组")
    if not (MIN_COMPOUNDS <= len(compounds) <= MAX_COMPOUNDS):
        _reject(
            "INVALID_COMPOUND_COUNT",
            f"化合物数量必须在 {MIN_COMPOUNDS} 到 {MAX_COMPOUNDS} 之间",
        )

    seen_ids = set()
    all_elements = set()
    normalised = []

    for index, compound in enumerate(compounds):
        label = f"compounds[{index}]"
        if not isinstance(compound, dict):
            _reject("INVALID_TYPE", f"{label} 必须是对象")

        unknown = set(compound) - COMPOUND_FIELDS
        if unknown:
            _reject("UNKNOWN_FIELD", f"{label} 存在未知字段: {sorted(unknown)}")
        for field in COMPOUND_FIELDS:
            if field not in compound:
                _reject("MISSING_FIELD", f"{label} 缺少 {field} 字段")

        compound_id = compound["id"]
        if not isinstance(compound_id, str) or not ID_PATTERN.match(compound_id):
            _reject("INVALID_ID", f"{label}.id 必须是非空 ASCII ID")
        if compound_id in seen_ids:
            _reject("DUPLICATE_ID", f"化合物 ID 重复: {compound_id}")
        seen_ids.add(compound_id)

        role = compound["role"]
        if not isinstance(role, str) or role not in ROLES:
            _reject("INVALID_ROLE", f"{label}.role 必须是 REACTANT 或 PRODUCT")

        composition = compound["composition"]
        if not isinstance(composition, dict):
            _reject("INVALID_TYPE", f"{label}.composition 必须是 JSON 对象")
        if not composition:
            _reject("EMPTY_COMPOSITION", f"{label} 组成不能为空")

        for symbol, count in composition.items():
            if not isinstance(symbol, str) or symbol not in ELEMENT_SYMBOLS:
                _reject("INVALID_ELEMENT", f"非法元素符号: {symbol!r}")
            if not _is_positive_int(count):
                _reject(
                    "INVALID_ELEMENT_COUNT",
                    f"{label}.composition.{symbol} 必须是正整数",
                )
        all_elements.update(composition)
        normalised.append(
            {"id": compound_id, "role": role, "composition": dict(composition)}
        )

    if len(all_elements) > MAX_ELEMENTS:
        _reject(
            "TOO_MANY_ELEMENTS",
            f"元素总数不得超过 {MAX_ELEMENTS} 种",
        )
    return normalised


def validate_verify_payload(payload: Any) -> Tuple[list, dict]:
    """Validate a /verify request body; coefficients may be any integer."""
    if not isinstance(payload, dict):
        _reject("INVALID_JSON", "请求体必须是 JSON 对象")

    unknown = set(payload) - {"compounds", "coefficients"}
    if unknown:
        _reject("UNKNOWN_FIELD", f"存在未知字段: {sorted(unknown)}")
    if "compounds" not in payload or "coefficients" not in payload:
        _reject("MISSING_FIELD", "缺少 compounds 或 coefficients 字段")

    compounds = validate_balance_payload(
        {"compounds": payload["compounds"]}
    )

    raw_coefficients = payload["coefficients"]
    if not isinstance(raw_coefficients, dict):
        _reject("INVALID_TYPE", "coefficients 必须是 JSON 对象")

    expected = {compound["id"] for compound in compounds}
    given = set(raw_coefficients)
    missing = expected - given
    extra = given - expected
    if missing:
        _reject("MISSING_COEFFICIENT", f"缺少系数: {sorted(missing)}")
    if extra:
        _reject("UNKNOWN_COEFFICIENT", f"未知化合物 ID: {sorted(extra)}")

    coefficients = {}
    for compound_id, value in raw_coefficients.items():
        if not isinstance(value, int) or isinstance(value, bool):
            _reject(
                "INVALID_COEFFICIENT",
                f"{compound_id} 的系数必须是整数",
            )
        coefficients[compound_id] = value
    return compounds, coefficients
