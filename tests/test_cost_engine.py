"""
test_cost_engine.py
===================
Comprehensive pytest test suite for the deterministic financial cost_engine.py.

Test Coverage:
1. Standard use cases (Clear Repair win, Clear Replace win)
2. Economic ties (exact equality, near-ties, tie-breaking behavior)
3. Mathematical models precision (C_repair, C_replace, annualized values)
4. Uncertainty handling (firm vs close verdicts, volatile parameter identification)
5. Flip assumption solver (find_flip_point human-readable sentences, numeric tipping points)
6. Edge cases (Q=0, p=0, p=1, v=0, high v, S>P, asymptotic energy dominance)
7. Input validation (missing keys, L_r <= 0, L_n <= 0, p not in [0, 1], negative values, case-insensitivity)
"""

import math
import os
import sys
import pytest
from typing import Dict, Any

_tests_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_tests_dir)
_backend_dir = os.path.join(_root_dir, "backend")
for _p in [_root_dir, _backend_dir, _tests_dir]:
    if os.path.isdir(_p) and _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from backend.cost_engine import (
        CostInputs,
        calculate_annualized_costs,
        calculate_flip_points,
        find_flip_point,
        run_uncertainty_analysis,
    )
except ImportError:
    from cost_engine import (
        CostInputs,
        calculate_annualized_costs,
        calculate_flip_points,
        find_flip_point,
        run_uncertainty_analysis,
    )


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def clear_repair_inputs() -> Dict[str, Any]:
    """Typical scenario where a minor repair is heavily favored."""
    return {
        "Q": 150.0,       # $150 repair quote
        "tr": 2.0,        # 2 hours waiting
        "tn": 5.0,        # 5 hours shopping/delivery
        "v": 25.0,        # $25/hr time value
        "p": 0.10,        # 10% repeat failure risk
        "E_old": 120.0,   # $120/yr energy
        "E_new": 90.0,    # $90/yr energy
        "L_r": 3.0,       # 3 years extended life
        "L_n": 10.0,      # 10 years new life
        "P": 950.0,       # $950 new unit
        "D": 80.0,        # $80 delivery/install
        "S": 30.0,        # $30 scrap credit
    }


@pytest.fixture
def clear_replace_inputs() -> Dict[str, Any]:
    """Typical scenario where a major repair is uneconomical."""
    return {
        "Q": 650.0,       # $650 major repair (e.g., compressor/transmission)
        "tr": 4.0,        # 4 hours
        "tn": 3.0,        # 3 hours
        "v": 30.0,        # $30/hr time value
        "p": 0.35,        # 35% repeat failure risk
        "E_old": 220.0,   # $220/yr old inefficient energy
        "E_new": 80.0,    # $80/yr modern inverter energy
        "L_r": 1.5,       # Only lasts 1.5 years
        "L_n": 10.0,      # 10 years new life
        "P": 800.0,       # $800 new unit
        "D": 50.0,
        "S": 50.0,
    }


@pytest.fixture
def exact_tie_inputs() -> Dict[str, Any]:
    """Constructed scenario where annualized repair equals annualized replacement."""
    # A_replace = (1000 + 0 - 0 + 0) / 10 + 100 = 100 + 100 = 200 $/yr
    # A_repair = (200 * (1 + 0) + 0) / 2 + 100 = 100 + 100 = 200 $/yr
    return {
        "Q": 200.0,
        "tr": 0.0,
        "tn": 0.0,
        "v": 0.0,
        "p": 0.0,
        "E_old": 100.0,
        "E_new": 100.0,
        "L_r": 2.0,
        "L_n": 10.0,
        "P": 1000.0,
        "D": 0.0,
        "S": 0.0,
    }


# ============================================================================
# 1. STANDARD USE CASES
# ============================================================================

def test_clear_repair_verdict(clear_repair_inputs):
    """Verifies clear repair recommendation and cost arithmetic."""
    result = calculate_annualized_costs(clear_repair_inputs)

    assert result["verdict"] == "Repair"
    assert result["is_tie"] is False

    # Manual verification of formulas:
    # C_repair = Q + (tr * v) + (p * Q) + (E_old * L_r)
    # = 150 + (2 * 25) + (0.10 * 150) + (120 * 3)
    # = 150 + 50 + 15 + 360 = 575.0
    # A_repair = 575.0 / 3.0 = 191.67
    assert math.isclose(result["total_repair_cost"], 575.0, abs_tol=0.01)
    assert math.isclose(result["annual_repair_cost"], 191.67, abs_tol=0.01)

    # C_replace = P + D - S + (tn * v) + (E_new * L_n)
    # = 950 + 80 - 30 + (5 * 25) + (90 * 10)
    # = 1000 + 125 + 900 = 2025.0
    # A_replace = 2025.0 / 10.0 = 202.50
    assert math.isclose(result["total_replace_cost"], 2025.0, abs_tol=0.01)
    assert math.isclose(result["annual_replace_cost"], 202.50, abs_tol=0.01)

    # Annual savings = 202.50 - 191.67 = 10.83
    assert math.isclose(result["annual_savings"], 10.83, abs_tol=0.01)
    assert "Repair" in result["recommendation_summary"]


def test_clear_replace_verdict(clear_replace_inputs):
    """Verifies clear replace recommendation on expensive, risky repairs."""
    result = calculate_annualized_costs(clear_replace_inputs)

    assert result["verdict"] == "Replace"
    assert result["is_tie"] is False

    # C_repair = 650 + (4*30) + (0.35*650) + (220*1.5)
    # = 650 + 120 + 227.50 + 330 = 1327.50
    # A_repair = 1327.50 / 1.5 = 885.00
    assert math.isclose(result["total_repair_cost"], 1327.50, abs_tol=0.01)
    assert math.isclose(result["annual_repair_cost"], 885.00, abs_tol=0.01)

    # C_replace = 800 + 50 - 50 + (3*30) + (80*10)
    # = 800 + 90 + 800 = 1690.00
    # A_replace = 1690.00 / 10.0 = 169.00
    assert math.isclose(result["total_replace_cost"], 1690.00, abs_tol=0.01)
    assert math.isclose(result["annual_replace_cost"], 169.00, abs_tol=0.01)

    assert math.isclose(result["annual_savings"], 716.00, abs_tol=0.01)
    assert "Replace" in result["recommendation_summary"]


# ============================================================================
# 2. ECONOMIC TIES & NEAR-TIES
# ============================================================================

def test_exact_economic_tie(exact_tie_inputs):
    """Verifies exact tie handling ($0.00 difference)."""
    result = calculate_annualized_costs(exact_tie_inputs)

    assert result["is_tie"] is True
    # By convention, repair is favored on ties to avoid capital outlay and waste
    assert result["verdict"] == "Repair"
    assert math.isclose(result["annual_repair_cost"], 200.0, abs_tol=0.01)
    assert math.isclose(result["annual_replace_cost"], 200.0, abs_tol=0.01)
    assert math.isclose(result["annual_savings"], 0.0, abs_tol=0.01)
    assert "Tie" in result["recommendation_summary"]


def test_near_tie_within_tolerance():
    """Verifies that differences within tie_tolerance (e.g. $0.005) are flagged as ties."""
    inputs = {
        "Q": 200.005,
        "tr": 0.0, "tn": 0.0, "v": 0.0, "p": 0.0,
        "E_old": 100.0, "E_new": 100.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 1000.0, "D": 0.0, "S": 0.0,
    }
    result = calculate_annualized_costs(inputs, tie_tolerance=0.01)
    assert result["is_tie"] is True
    assert result["verdict"] == "Repair"


# ============================================================================
# 3. UNCERTAINTY HANDLING (FIRM VS CLOSE VERDICTS)
# ============================================================================

def test_firm_uncertainty_verdict(clear_replace_inputs):
    """Major repair should remain 'Replace' across all sensitivity scenarios."""
    result = calculate_annualized_costs(clear_replace_inputs)
    assert result["confidence"] == "firm"
    assert len(result["volatile_parameters"]) == 0
    assert result["volatile_parameter"] == "None"


def test_close_uncertainty_verdict_identifies_volatile_parameter():
    """
    Constructs a borderline scenario where a 20% shift in lifespan (L_r)
    flips the verdict, confirming 'close' label and identifying L_r as volatile.
    """
    # Baseline:
    # Replace: (900)/10 + 100 = 190 $/yr
    # Repair: (200)/1.1 + 0 = 181.8 $/yr (Repair wins slightly)
    # If L_r drops by 20% from 1.1 to 0.88:
    # Repair becomes: 200 / 0.88 = 227.27 $/yr -> Flips to Replace!
    borderline_inputs = {
        "Q": 200.0,
        "tr": 0.0, "tn": 0.0, "v": 0.0, "p": 0.0,
        "E_old": 0.0, "E_new": 100.0,
        "L_r": 1.1, "L_n": 10.0,
        "P": 900.0, "D": 0.0, "S": 0.0,
    }

    result = calculate_annualized_costs(borderline_inputs, sensitivity_pct=0.20)
    assert result["confidence"] == "close"
    assert "L_r" in result["volatile_parameters"]
    assert result["volatile_parameter"] == "L_r"


def test_failure_probability_volatility():
    """Verifies that failure risk 'p' is flagged when it causes a flip."""
    # Repair: (300*(1+p)) / 2 = 150 * (1+p)
    # At p=0.10: 150 * 1.10 = 165 $/yr (Repair wins vs Replace at 175)
    # At high p=0.30: 150 * 1.30 = 195 $/yr (Flips to Replace)
    inputs = {
        "Q": 300.0,
        "tr": 0.0, "tn": 0.0, "v": 0.0,
        "p": 0.15,
        "E_old": 0.0, "E_new": 0.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 1750.0, "D": 0.0, "S": 0.0,
    }
    result = calculate_annualized_costs(inputs, sensitivity_pct=0.25)
    assert result["confidence"] == "close"
    assert "p" in result["volatile_parameters"]


# ============================================================================
# 4. FLIP ASSUMPTION SOLVER (find_flip_point)
# ============================================================================

def test_find_flip_point_replace_to_repair():
    """Tests tipping point calculation when base verdict is Replace."""
    # Base:
    # A_replace = 1000/10 + 100 = 200 $/yr
    # A_repair = 400/2 + 100 = 300 $/yr -> Replace wins
    # To flip: 400 / L_r* + 100 == 200  =>  400 / L_r* = 100  =>  L_r* = 4.0 years
    # Or Q*: Q* / 2 + 100 == 200  =>  Q*/2 = 100  =>  Q* = 200
    inputs = {
        "Q": 400.0,
        "tr": 0.0, "tn": 0.0, "v": 0.0, "p": 0.0,
        "E_old": 100.0, "E_new": 100.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 1000.0, "D": 0.0, "S": 0.0,
    }

    sentence = find_flip_point(inputs)
    assert "To flip the verdict to Repair" in sentence
    assert "at least 4.0 years" in sentence
    assert "currently 2.0 years" in sentence
    assert "$200.00" in sentence  # Quote flip point

    flip_data = calculate_flip_points(inputs)
    assert math.isclose(flip_data["tipping_points"]["L_r"], 4.0, abs_tol=0.01)
    assert math.isclose(flip_data["tipping_points"]["Q"], 200.0, abs_tol=0.01)


def test_find_flip_point_repair_to_replace():
    """Tests tipping point calculation when base verdict is Repair."""
    # Base:
    # A_replace = 2000/10 + 100 = 300 $/yr
    # A_repair = 200/2 + 100 = 200 $/yr -> Repair wins
    # To flip to Replace:
    # 200 / L_r* + 100 == 300  =>  L_r* = 200/200 = 1.0 year
    # Q* rise: Q* / 2 + 100 == 300  =>  Q* = 400
    inputs = {
        "Q": 200.0,
        "tr": 0.0, "tn": 0.0, "v": 0.0, "p": 0.0,
        "E_old": 100.0, "E_new": 100.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 2000.0, "D": 0.0, "S": 0.0,
    }

    sentence = find_flip_point(inputs)
    assert "To flip the verdict to Replace" in sentence
    assert "drop below 1.0 years" in sentence
    assert "currently 2.0 years" in sentence
    assert "$400.00" in sentence  # Quote must rise above $400


def test_find_flip_point_asymptotic_energy_dominance():
    """
    Tests edge case where old operating cost (E_old) alone exceeds total
    annualized replacement cost (A_replace <= E_old).
    Extended lifespan alone can NEVER make repair cheaper.
    """
    # A_replace = 800/10 + 80 = 160 $/yr
    # E_old = 200 $/yr
    # A_repair = K_r / L_r + 200 > 200 > 160 for any positive L_r!
    inputs = {
        "Q": 300.0,
        "tr": 0.0, "tn": 0.0, "v": 0.0, "p": 0.0,
        "E_old": 200.0,
        "E_new": 80.0,
        "L_r": 2.0,
        "L_n": 10.0,
        "P": 800.0,
        "D": 0.0,
        "S": 0.0,
    }

    sentence = find_flip_point(inputs)
    # Must correctly recognize that L_r alone cannot flip the decision
    assert "extending repair lifespan alone cannot flip" in sentence.lower() or "operating costs" in sentence.lower()


def test_find_flip_point_on_exact_tie(exact_tie_inputs):
    """Verifies flip point message when already in economic tie."""
    sentence = find_flip_point(exact_tie_inputs)
    assert "economic tie" in sentence.lower()


# ============================================================================
# 5. MATHEMATICAL BOUNDARY & EDGE CASES
# ============================================================================

def test_zero_repair_quote_and_time():
    """Edge case: Free warranty repair (Q=0, tr=0)."""
    inputs = {
        "Q": 0.0, "tr": 0.0, "tn": 2.0, "v": 20.0, "p": 0.0,
        "E_old": 100.0, "E_new": 100.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 800.0, "D": 0.0, "S": 0.0,
    }
    result = calculate_annualized_costs(inputs)
    assert result["verdict"] == "Repair"
    assert math.isclose(result["annual_repair_cost"], 100.0, abs_tol=0.01)


def test_p_equals_zero_and_one():
    """Tests boundary probabilities p=0.0 (no risk) and p=1.0 (certain failure)."""
    base = {
        "Q": 200.0, "tr": 0.0, "tn": 0.0, "v": 0.0,
        "E_old": 50.0, "E_new": 50.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 1200.0, "D": 0.0, "S": 0.0,
    }

    # At p=0.0, repair risk cost is $0
    res_p0 = calculate_annualized_costs({**base, "p": 0.0})
    assert res_p0["breakdown"]["repair"]["repeat_failure_risk_cost"] == 0.0
    assert math.isclose(res_p0["annual_repair_cost"], 150.0, abs_tol=0.01)

    # At p=1.0, repair risk cost equals full quote $200
    res_p1 = calculate_annualized_costs({**base, "p": 1.0})
    assert res_p1["breakdown"]["repair"]["repeat_failure_risk_cost"] == 200.0
    # C_repair = 200 + 200 + (50 * 2) = 500  =>  A_repair = 250.0
    assert math.isclose(res_p1["annual_repair_cost"], 250.0, abs_tol=0.01)


def test_high_time_value_impacts_decision():
    """
    When user's time value (v) is high and repair takes much longer than replacing,
    hassle cost tips verdict to Replace.
    """
    inputs = {
        "Q": 200.0,
        "tr": 10.0,        # 10 hours lost waiting for technician
        "tn": 1.0,         # 1 hour one-click online ordering
        "v": 150.0,        # High-earner $150/hr
        "p": 0.0,
        "E_old": 50.0, "E_new": 50.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 1200.0, "D": 0.0, "S": 0.0,
    }
    result = calculate_annualized_costs(inputs)
    # tr * v = 1500. Total repair = 200 + 1500 + 100 = 1800. Annual = 900 $/yr!
    # tn * v = 150. Total replace = 1200 + 150 + 500 = 1850. Annual = 185 $/yr!
    assert result["verdict"] == "Replace"
    assert math.isclose(result["breakdown"]["repair"]["time_hassle_cost"], 1500.0)


def test_salvage_credit_greater_than_zero():
    """Verifies that salvage/rebate (S) reduces net replacement capital outlay."""
    inputs = {
        "Q": 300.0, "tr": 0.0, "tn": 0.0, "v": 0.0, "p": 0.0,
        "E_old": 100.0, "E_new": 100.0,
        "L_r": 2.0, "L_n": 10.0,
        "P": 1000.0, "D": 50.0, "S": 200.0,
    }
    result = calculate_annualized_costs(inputs)
    # Net capital outlay = 1000 + 50 - 200 = 850
    assert math.isclose(result["breakdown"]["replace"]["net_capital_outlay"], 850.0)


# ============================================================================
# 6. INPUT VALIDATION & ERROR HANDLING
# ============================================================================

def test_missing_required_keys_raises_value_error():
    """Missing variables must raise a clear ValueError."""
    with pytest.raises(ValueError, match="Missing required cost engine variable"):
        calculate_annualized_costs({"Q": 100.0, "P": 500.0})


def test_non_positive_lifespan_raises_value_error(clear_repair_inputs):
    """Lifespans L_r and L_n must be strictly positive to prevent division by zero."""
    with pytest.raises(ValueError, match="L_r.*strictly positive"):
        calculate_annualized_costs({**clear_repair_inputs, "L_r": 0.0})

    with pytest.raises(ValueError, match="L_r.*strictly positive"):
        calculate_annualized_costs({**clear_repair_inputs, "L_r": -1.5})

    with pytest.raises(ValueError, match="L_n.*strictly positive"):
        calculate_annualized_costs({**clear_repair_inputs, "L_n": 0.0})


def test_probability_out_of_bounds_raises_value_error(clear_repair_inputs):
    """Failure probability p must be in [0.0, 1.0]."""
    with pytest.raises(ValueError, match="probability 'p' must be between 0.0 and 1.0"):
        calculate_annualized_costs({**clear_repair_inputs, "p": 1.25})

    with pytest.raises(ValueError, match="probability 'p' must be between 0.0 and 1.0"):
        calculate_annualized_costs({**clear_repair_inputs, "p": -0.05})


def test_negative_costs_raise_value_error(clear_repair_inputs):
    """Negative prices or quotes must raise ValueError."""
    with pytest.raises(ValueError, match="Repair quote 'Q' cannot be negative"):
        calculate_annualized_costs({**clear_repair_inputs, "Q": -50.0})

    with pytest.raises(ValueError, match="Replacement price 'P' cannot be negative"):
        calculate_annualized_costs({**clear_repair_inputs, "P": -500.0})


def test_case_insensitive_and_string_number_inputs():
    """Verifies that lowercase keys and string-formatted numbers are parsed cleanly."""
    lowercase_inputs = {
        "q": "200.0",
        "tr": "1.5",
        "tn": "2.0",
        "v": "20",
        "p": "0.1",
        "e_old": "100",
        "e_new": "80",
        "l_r": "2.5",
        "l_n": "10",
        "price": "900",
        "d": "50",
        "s": "25",
    }
    result = calculate_annualized_costs(lowercase_inputs)
    assert result["verdict"] in ("Repair", "Replace")
    assert isinstance(result["annual_repair_cost"], float)


# ============================================================================
# STANDALONE EXECUTION RUNNER
# ============================================================================

if __name__ == "__main__":
    pytest.main(["-v", __file__])

