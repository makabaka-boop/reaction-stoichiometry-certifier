"""Exhaustive integer cross-checks of the rational solver on small matrices.

For every small integer composition matrix we independently brute-force the
*positive integer* kernel (bounded coefficient search), reduce every hit to
its primitive vector, and compare against the exact Gaussian-elimination
result.  The two implementations share no code.
"""

from __future__ import annotations

from itertools import product
from math import gcd

import pytest

from app.balancing import balance, to_primitive_integers
from fractions import Fraction


def brute_force_primitives(matrix, roles, *, bound=6):
    """Enumerate positive coefficient tuples that satisfy ``matrix @ x = 0``.

    Returns the set of unique primitive integer solutions with a fixed sign
    convention (first non-free... simply the tuple as enumerated, then
    canonicalised so a tuple and its scalar multiples collapse together).
    """
    n = len(roles)
    signed = [
        [entry if roles[col] == "REACTANT" else -entry
         for col, entry in enumerate(row)]
        for row in matrix
    ]
    found = set()
    for vector in product(range(1, bound + 1), repeat=n):
        if all(
            sum(row[c] * vector[c] for c in range(n)) == 0 for row in signed
        ):
            common = vector[0]
            for value in vector[1:]:
                common = gcd(common, value)
            found.add(tuple(value // common for value in vector))
    return found


def solve(matrix, roles):
    compounds = [
        {
            "id": f"C{i}",
            "role": role,
            "composition": {
                f"E{r}": value for r, row in enumerate(matrix) for value in [row[i]] if value
            },
        }
        for i, role in enumerate(roles)
    ]
    return balance(compounds)


# ---------------------------------------------------------------------------
# Two compounds, one/two elements, counts in 1..3: fully enumerated.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("entries", product(range(1, 4), repeat=4))
def test_two_compounds_exhaustive(entries):
    # Two element rows: [[a, b], [c, d]], both compounds present.
    a, b, c, d = entries
    matrix = [[a, b], [c, d]]
    roles = ("REACTANT", "PRODUCT")

    result = solve(matrix, roles)
    primitives = brute_force_primitives(matrix, roles, bound=12)

    if not primitives:
        assert result["status"] in {"NO_BALANCE", "NO_POSITIVE_BALANCE"}
    else:
        # One equation in two unknowns => at most one primitive direction.
        assert result["status"] == "BALANCED"
        answer = tuple(item["coefficient"] for item in result["coefficients"])
        assert answer in primitives
        # Hand-verifiable conservation for every element row.
        for row in matrix:
            assert row[0] * answer[0] == row[1] * answer[1]


# ---------------------------------------------------------------------------
# Three compounds, one element, counts in 1..3: fully enumerated, every
# reactant/product placement.  Covers NO_BALANCE, unique and underdetermined.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("counts", product(range(1, 4), repeat=3))
@pytest.mark.parametrize("role_pattern", [
    ("REACTANT", "PRODUCT", "PRODUCT"),
    ("REACTANT", "REACTANT", "PRODUCT"),
    ("REACTANT", "REACTANT", "REACTANT"),
])
def test_three_compounds_one_element_exhaustive(counts, role_pattern):
    matrix = [list(counts)]
    result = solve(matrix, role_pattern)
    primitives = brute_force_primitives(matrix, role_pattern, bound=10)

    if result["status"] == "BALANCED":
        answer = tuple(item["coefficient"] for item in result["coefficients"])
        assert answer in primitives
        common = answer[0]
        for value in answer[1:]:
            common = gcd(common, value)
        assert common == 1
    elif result["status"] == "UNDERDETERMINED":
        # Nullity 2 with one all-positive generator pair (or all-same-side
        # where nothing positive can exist); brute force must agree that
        # there is not exactly one primitive solution.
        assert len(primitives) != 1
    elif result["status"] == "NO_POSITIVE_BALANCE":
        # A one-dimensional kernel that cannot be oriented positive.
        assert primitives == set()
    else:
        assert result["status"] == "NO_BALANCE"
        assert primitives == set()


# ---------------------------------------------------------------------------
# Known, item-by-item verifiable reactions.
# ---------------------------------------------------------------------------

KNOWN_REACTIONS = [
    # 2 H2 + O2 -> 2 H2O
    (
        [
            {"id": "H2", "role": "REACTANT", "composition": {"H": 2}},
            {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
            {"id": "H2O", "role": "PRODUCT", "composition": {"H": 2, "O": 1}},
        ],
        {"H2": 2, "O2": 1, "H2O": 2},
    ),
    # CH4 + 2 O2 -> CO2 + 2 H2O
    (
        [
            {"id": "CH4", "role": "REACTANT", "composition": {"C": 1, "H": 4}},
            {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
            {"id": "CO2", "role": "PRODUCT", "composition": {"C": 1, "O": 2}},
            {"id": "H2O", "role": "PRODUCT", "composition": {"H": 2, "O": 1}},
        ],
        {"CH4": 1, "O2": 2, "CO2": 1, "H2O": 2},
    ),
    # 4 Fe + 3 O2 -> 2 Fe2O3
    (
        [
            {"id": "Fe", "role": "REACTANT", "composition": {"Fe": 1}},
            {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
            {"id": "Fe2O3", "role": "PRODUCT", "composition": {"Fe": 2, "O": 3}},
        ],
        {"Fe": 4, "O2": 3, "Fe2O3": 2},
    ),
    # 2 C8H18 + 25 O2 -> 16 CO2 + 18 H2O (large LCM, still exact)
    (
        [
            {"id": "C8H18", "role": "REACTANT", "composition": {"C": 8, "H": 18}},
            {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
            {"id": "CO2", "role": "PRODUCT", "composition": {"C": 1, "O": 2}},
            {"id": "H2O", "role": "PRODUCT", "composition": {"H": 2, "O": 1}},
        ],
        {"C8H18": 2, "O2": 25, "CO2": 16, "H2O": 18},
    ),
]


@pytest.mark.parametrize("compounds,expected", KNOWN_REACTIONS)
def test_known_reactions(compounds, expected):
    result = balance(compounds)
    assert result["status"] == "BALANCED"
    answer = {item["id"]: item["coefficient"] for item in result["coefficients"]}
    assert answer == expected

    # Coefficients are collectively coprime.
    values = list(answer.values())
    common = values[0]
    for value in values[1:]:
        common = gcd(common, value)
    assert common == 1

    # Element totals match on both sides.
    for symbol, totals in result["elementTotals"].items():
        assert totals["reactant"] == totals["product"], symbol
        assert totals["reactant"] > 0


def test_no_balance():
    # CH4 + O2 -> CO2: hydrogen vanishes, no conservation solution at all.
    compounds = [
        {"id": "CH4", "role": "REACTANT", "composition": {"C": 1, "H": 4}},
        {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
        {"id": "CO2", "role": "PRODUCT", "composition": {"C": 1, "O": 2}},
    ]
    result = balance(compounds)
    assert result["status"] == "NO_BALANCE"
    assert result["nullity"] == 0
    assert result["reason"] == "ZERO_NULLSPACE"


def test_underdetermined():
    # H2 + C + O2 -> H2O + CO + CO2 has a 2-dimensional null space.
    compounds = [
        {"id": "H2", "role": "REACTANT", "composition": {"H": 2}},
        {"id": "C", "role": "REACTANT", "composition": {"C": 1}},
        {"id": "O2", "role": "REACTANT", "composition": {"O": 2}},
        {"id": "H2O", "role": "PRODUCT", "composition": {"H": 2, "O": 1}},
        {"id": "CO", "role": "PRODUCT", "composition": {"C": 1, "O": 1}},
        {"id": "CO2", "role": "PRODUCT", "composition": {"C": 1, "O": 2}},
    ]
    result = balance(compounds)
    assert result["status"] == "UNDERDETERMINED"
    assert result["nullity"] > 1


def test_no_positive_zero_coefficient():
    # A + B -> C with [1, 2, ?]... build kernel vector (1, -1, 0): the only
    # conservation solution leaves C out entirely.
    compounds = [
        {"id": "A", "role": "REACTANT", "composition": {"X": 1}},
        {"id": "B", "role": "REACTANT", "composition": {"X": 1}},
        {"id": "C", "role": "PRODUCT", "composition": {"Y": 1}},
    ]
    result = balance(compounds)
    assert result["status"] == "NO_POSITIVE_BALANCE"
    assert result["reason"] == "ZERO_COEFFICIENT"


def test_no_positive_mixed_signs():
    # Three reactants, one element, rank 2: kernel dim 1 with mixed signs.
    # Element rows chosen so x = (1, 1, -1) is the kernel:
    # row (1,-1,0): x1 - x2 = 0 ; row (0,1,-1): x2 - x3 = 0 -> x1=x2=x3
    # All positive would solve that, so use rows (1,1,0) and (0,1,1):
    # x1 + x2 = 0 and x2 + x3 = 0 -> (1, -1, 1).
    compounds = [
        {"id": "A", "role": "REACTANT", "composition": {"X": 1}},
        {"id": "B", "role": "REACTANT", "composition": {"X": 1, "Y": 1}},
        {"id": "C", "role": "REACTANT", "composition": {"Y": 1}},
    ]
    result = balance(compounds)
    assert result["status"] == "NO_POSITIVE_BALANCE"
    assert result["reason"] == "MIXED_SIGNS"


def test_integer_normalisation_lcm_then_gcd():
    # (1/2, 1/3, 1/6) -> LCM 6 -> (3, 2, 1), already primitive.
    assert to_primitive_integers([Fraction(1, 2), Fraction(1, 3), Fraction(1, 6)]) == [
        3,
        2,
        1,
    ]
    # (2/3, 4/3) -> (2, 4) -> gcd 2 -> (1, 2).
    assert to_primitive_integers([Fraction(2, 3), Fraction(4, 3)]) == [1, 2]
