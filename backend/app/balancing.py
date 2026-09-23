"""Exact chemical-equation balancing with rational arithmetic.

The conservation matrix has one row per element and one column per compound.
Reactant columns carry +count entries, product columns carry -count entries.
Stoichiometric coefficients live in the *right* null space of that matrix:
``matrix @ x = 0``.

Every number here is a :class:`fractions.Fraction`, so near-zero pivots can
never be mistaken for real constraints and the free variables are chosen by
the pivot structure of the exact reduced row-echelon form.
"""

from __future__ import annotations

from fractions import Fraction
from math import gcd
from typing import List, Sequence

ZERO = Fraction(0)
ONE = Fraction(1)


# ---------------------------------------------------------------------------
# Matrix construction
# ---------------------------------------------------------------------------

def build_matrix(
    compounds: Sequence[dict],
    elements: Sequence[str],
) -> List[List[Fraction]]:
    """Build the element conservation matrix.

    Reactants contribute positively, products negatively. ``elements`` is the
    ordered list of element symbols that determines the row order.
    """
    index = {symbol: row for row, symbol in enumerate(elements)}
    matrix = [[ZERO] * len(compounds) for _ in elements]
    for col, compound in enumerate(compounds):
        sign = 1 if compound["role"] == "REACTANT" else -1
        for symbol, count in compound["composition"].items():
            matrix[index[symbol]][col] = Fraction(sign * count)
    return matrix


# ---------------------------------------------------------------------------
# Rational Gaussian elimination
# ---------------------------------------------------------------------------

def rref(matrix: Sequence[Sequence[Fraction]]) -> List[List[Fraction]]:
    """Return the reduced row-echelon form of ``matrix`` using exact rationals."""
    result = [list(row) for row in matrix]
    if not result:
        return result
    rows = len(result)
    cols = len(result[0])

    pivot_row = 0
    for col in range(cols):
        pivot = next(
            (r for r in range(pivot_row, rows) if result[r][col] != ZERO),
            None,
        )
        if pivot is None:
            continue

        result[pivot_row], result[pivot] = result[pivot], result[pivot_row]

        pivot_value = result[pivot_row][col]
        result[pivot_row] = [value / pivot_value for value in result[pivot_row]]

        for r in range(rows):
            if r != pivot_row and result[r][col] != ZERO:
                factor = result[r][col]
                result[r] = [
                    value - factor * above
                    for value, above in zip(result[r], result[pivot_row])
                ]
        pivot_row += 1
        if pivot_row == rows:
            break
    return result


def nullspace(reduced: Sequence[Sequence[Fraction]], cols: int) -> List[List[Fraction]]:
    """Extract a basis of the right null space from a RREF matrix.

    One basis vector is returned per free variable; pivot coordinates are
    read straight off the negated RREF rows, so no arbitrary pivoting or
    floating tolerance is involved.
    """
    pivot_cols = []
    for row in reduced:
        pivot = next((c for c, value in enumerate(row) if value != ZERO), None)
        if pivot is not None:
            pivot_cols.append(pivot)

    free_cols = [c for c in range(cols) if c not in pivot_cols]
    vectors: List[List[Fraction]] = []
    for free in free_cols:
        vector = [ZERO] * cols
        vector[free] = ONE
        for row, pivot in zip(reduced, pivot_cols):
            vector[pivot] = -row[free]
        vectors.append(vector)
    return vectors


# ---------------------------------------------------------------------------
# Integer normalisation
# ---------------------------------------------------------------------------

def to_primitive_integers(vector: Sequence[Fraction]) -> List[int]:
    """Scale a rational vector to coprime integers (LCM of denominators / GCD)."""
    denominators = [value.denominator for value in vector]
    scale = denominators[0]
    for denominator in denominators[1:]:
        scale = scale * denominator // gcd(scale, denominator)

    integers = [int(value * scale) for value in vector]
    common = abs(integers[0])
    for value in integers[1:]:
        common = gcd(common, abs(value))
    if common > 1:
        integers = [value // common for value in integers]
    return integers


def nullity(matrix: Sequence[Sequence[Fraction]], cols: int) -> int:
    return len(nullspace(rref(matrix), cols))


# ---------------------------------------------------------------------------
# Balancing
# ---------------------------------------------------------------------------

def element_totals(compounds: Sequence[dict], coefficients: Sequence[int]) -> dict:
    """Count every element on each side given the primitive coefficients."""
    totals = {}
    for compound, coefficient in zip(compounds, coefficients):
        for symbol, count in compound["composition"].items():
            entry = totals.setdefault(symbol, {"reactant": 0, "product": 0})
            side = "reactant" if compound["role"] == "REACTANT" else "product"
            entry[side] += coefficient * count
    return totals


def balance(compounds: Sequence[dict]) -> dict:
    """Return the certification result for an already-validated payload.

    Statuses:
      * ``BALANCED``           - nullity one, generator can be made all positive
      * ``NO_BALANCE``         - nullity zero, no conservation solution exists
      * ``UNDERDETERMINED``    - nullity above one, infinitely many solutions
      * ``NO_POSITIVE_BALANCE``- nullity one but the solution has zeros or
                                 cannot be oriented so every coefficient is
                                 strictly positive
    """
    elements = sorted(
        {symbol for compound in compounds for symbol in compound["composition"]}
    )
    matrix = build_matrix(compounds, elements)
    basis = nullspace(rref(matrix), len(compounds))

    if len(basis) == 0:
        return {
            "status": "NO_BALANCE",
            "nullity": 0,
            "reason": "ZERO_NULLSPACE",
        }
    if len(basis) > 1:
        return {
            "status": "UNDERDETERMINED",
            "nullity": len(basis),
            "reason": "NULLSPACE_DIMENSION_GT_ONE",
        }

    generator = basis[0]
    if any(value == ZERO for value in generator):
        return {
            "status": "NO_POSITIVE_BALANCE",
            "nullity": 1,
            "reason": "ZERO_COEFFICIENT",
        }

    first = next(value for value in generator if value != ZERO)
    if first < 0:
        generator = [-value for value in generator]
    # Only an overall sign flip is allowed; mixed signs cannot be repaired.
    if any(value < ZERO for value in generator):
        return {
            "status": "NO_POSITIVE_BALANCE",
            "nullity": 1,
            "reason": "MIXED_SIGNS",
        }

    coefficients = to_primitive_integers(generator)
    return {
        "status": "BALANCED",
        "nullity": 1,
        "reason": "UNIQUE_PRIMITIVE_SOLUTION",
        "coefficients": [
            {"id": compound["id"], "coefficient": coefficient}
            for compound, coefficient in zip(compounds, coefficients)
        ],
        "elementTotals": element_totals(compounds, coefficients),
    }


# ---------------------------------------------------------------------------
# Manual coefficient verification
# ---------------------------------------------------------------------------

def verify(compounds: Sequence[dict], coefficients: dict) -> dict:
    """Check reviewer-supplied integer coefficients for conservation/minimality."""
    elements = sorted(
        {symbol for compound in compounds for symbol in compound["composition"]}
    )
    ordered = [int(coefficients[compound["id"]]) for compound in compounds]

    totals = {}
    elementChecks = {}
    conserved = True
    for row, symbol in enumerate(elements):
        reactant_total = 0
        product_total = 0
        for col, compound in enumerate(compounds):
            count = compound["composition"].get(symbol, 0)
            if count:
                side_total = ordered[col] * count
                if compound["role"] == "REACTANT":
                    reactant_total += side_total
                else:
                    product_total += side_total
        totals[symbol] = {"reactant": reactant_total, "product": product_total}
        balanced = reactant_total == product_total
        elementChecks[symbol] = {
            "reactant": reactant_total,
            "product": product_total,
            "balanced": balanced,
        }
        conserved = conserved and balanced

    common = abs(ordered[0])
    for value in ordered[1:]:
        common = gcd(common, abs(value))
    gcd_one = common == 1
    all_positive = all(value > 0 for value in ordered)

    balanced = conserved and all_positive
    primitive = balanced and gcd_one

    reasons = []
    if not all_positive:
        reasons.append("NON_POSITIVE_COEFFICIENT")
    if not conserved:
        reasons.append("ELEMENT_NOT_CONSERVED")
    if balanced and not gcd_one:
        reasons.append("NOT_PRIMITIVE_GCD_" + str(common))

    return {
        "balanced": balanced,
        "primitive": primitive,
        "gcd": common,
        "allPositive": all_positive,
        "reasons": reasons,
        "elementChecks": elementChecks,
        "elementTotals": totals,
    }
