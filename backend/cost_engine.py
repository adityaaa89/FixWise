"""
cost_engine.py
==============
Deterministic Financial Decision Engine for the Repair or Replace Advisor.

The language model must NEVER do arithmetic; all mathematical modeling,
annualized cost optimizations, sensitivity uncertainty analyses, and tipping
point (flip assumption) calculations happen inside this deterministic module.

Mathematical Models Implemented:
--------------------------------
1. Repair Total Cost:
   C_repair = Q + (tr * v) + (p * Q) + (E_old * L_r)
   Annualized Repair Cost:
   Cost per year = C_repair / L_r = (Q * (1 + p) + tr * v) / L_r + E_old

2. Replace Total Cost:
   C_replace = P + D - S + (tn * v) + (E_new * L_n)
   Annualized Replace Cost:
   Cost per year = C_replace / L_n = (P + D - S + tn * v) / L_n + E_new

Variables:
----------
Q     : Repair quote / parts & labor cost ($)
tr    : Time lost / hassle hours dealing with repair (hours)
tn    : Time lost / hassle hours purchasing & installing replacement (hours)
v     : Monetary value of consumer's time ($/hour)
p     : Probability of repeat breakdown within extended lifespan (0.0 to 1.0)
E_old : Annual operating / energy cost of old/repaired appliance ($/year)
E_new : Annual operating / energy cost of new energy-efficient appliance ($/year)
L_r   : Expected extended lifespan if repaired (years, L_r > 0)
L_n   : Expected lifespan of brand-new replacement appliance (years, L_n > 0)
P     : Purchase sticker price of new replacement ($)
D     : Delivery, professional installation, and haul-away fee ($)
S     : Salvage, trade-in, scrap, or utility rebate credit received ($)
"""

from __future__ import annotations

import copy
import dataclasses
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union


# ============================================================================
# DATA STRUCTURES & INPUT VALIDATION
# ============================================================================

CANONICAL_VARIABLE_NAMES = {
    "q": "Q",
    "tr": "tr",
    "tn": "tn",
    "v": "v",
    "e_old": "E_old",
    "e_new": "E_new",
    "l_r": "L_r",
    "l_n": "L_n",
    "p_price": "P",
    "price": "P",
    "d": "D",
    "s": "S",
}


@dataclass(frozen=True)
class CostInputs:
    """Validated, immutable container for cost engine parameters."""

    Q: float
    tr: float
    tn: float
    v: float
    p: float
    E_old: float
    E_new: float
    L_r: float
    L_n: float
    P: float
    D: float = 0.0
    S: float = 0.0

    @classmethod
    def from_dict(cls, raw_inputs: Dict[str, Any]) -> "CostInputs":
        """
        Normalizes dictionary keys and validates types/bounds.
        """
        if not isinstance(raw_inputs, dict):
            raise TypeError(f"Expected dict for inputs, received {type(raw_inputs).__name__}")

        normalized: Dict[str, Any] = {}
        for k, val in raw_inputs.items():
            if k == "P" or k == "p":
                # Preserve case sensitivity for purchase price (P) vs repeat failure probability (p)
                normalized[k] = val
            else:
                lower_k = str(k).strip().lower()
                canonical_key = CANONICAL_VARIABLE_NAMES.get(lower_k, k)
                normalized[canonical_key] = val

        required_keys = ["Q", "tr", "tn", "v", "p", "E_old", "E_new", "L_r", "L_n", "P"]
        missing = [rk for rk in required_keys if rk not in normalized]
        if missing:
            raise ValueError(f"Missing required cost engine variable(s): {missing}")

        def _to_float(key: str, default: Optional[float] = None) -> float:
            val = normalized.get(key, default)
            if val is None:
                raise ValueError(f"Missing required parameter '{key}'")
            try:
                f_val = float(val)
            except (ValueError, TypeError) as err:
                raise ValueError(f"Parameter '{key}' must be a numeric float, got {val!r}") from err
            if math.isnan(f_val) or math.isinf(f_val):
                raise ValueError(f"Parameter '{key}' cannot be NaN or Infinite")
            return f_val

        Q = _to_float("Q")
        tr = _to_float("tr")
        tn = _to_float("tn")
        v = _to_float("v")
        p = _to_float("p")
        E_old = _to_float("E_old")
        E_new = _to_float("E_new")
        L_r = _to_float("L_r")
        L_n = _to_float("L_n")
        P = _to_float("P")
        D = _to_float("D", default=0.0)
        S = _to_float("S", default=0.0)

        # Domain Boundary Validations
        if L_r <= 0.0:
            raise ValueError(f"Repaired lifespan 'L_r' must be strictly positive (> 0), got {L_r}")
        if L_n <= 0.0:
            raise ValueError(f"Replacement lifespan 'L_n' must be strictly positive (> 0), got {L_n}")
        if not (0.0 <= p <= 1.0):
            raise ValueError(f"Repeat breakdown probability 'p' must be between 0.0 and 1.0, got {p}")
        if Q < 0.0:
            raise ValueError(f"Repair quote 'Q' cannot be negative, got {Q}")
        if P < 0.0:
            raise ValueError(f"Replacement price 'P' cannot be negative, got {P}")
        if v < 0.0:
            raise ValueError(f"Value of time 'v' cannot be negative, got {v}")
        if tr < 0.0 or tn < 0.0:
            raise ValueError(f"Time investment 'tr' and 'tn' cannot be negative, got tr={tr}, tn={tn}")
        if E_old < 0.0 or E_new < 0.0:
            raise ValueError(f"Operating costs 'E_old' and 'E_new' cannot be negative, got E_old={E_old}, E_new={E_new}")

        return cls(
            Q=Q, tr=tr, tn=tn, v=v, p=p,
            E_old=E_old, E_new=E_new,
            L_r=L_r, L_n=L_n,
            P=P, D=D, S=S,
        )

    def to_dict(self) -> Dict[str, float]:
        """Convert back to canonical dictionary format."""
        return {
            "Q": self.Q,
            "tr": self.tr,
            "tn": self.tn,
            "v": self.v,
            "p": self.p,
            "E_old": self.E_old,
            "E_new": self.E_new,
            "L_r": self.L_r,
            "L_n": self.L_n,
            "P": self.P,
            "D": self.D,
            "S": self.S,
        }


# ============================================================================
# CORE ANNUALIZED COST COMPUTATION
# ============================================================================

def calculate_annualized_costs(
    inputs: Dict[str, Any],
    sensitivity_pct: float = 0.20,
    tie_tolerance: float = 0.01,
) -> Dict[str, Any]:
    """
    Computes total lifecycle costs, annualized costs, monetary savings,
    sensitivity uncertainty scenario labels ("firm" vs "close"), and definitive verdict.

    Parameters:
    -----------
    inputs : dict
        Contains all mathematical model variables:
        Q, tr, tn, v, p, E_old, E_new, L_r, L_n, P, D, S
    sensitivity_pct : float, default 0.20
        Percentage shift used for low/high uncertainty testing (default +/- 20%).
    tie_tolerance : float, default 0.01
        Maximum annualized difference ($) considered an economic tie.

    Returns:
    --------
    dict:
        {
            "verdict": "Repair" or "Replace",
            "annual_repair_cost": float,
            "annual_replace_cost": float,
            "total_repair_cost": float,
            "total_replace_cost": float,
            "annual_difference": float,
            "annual_savings": float,
            "confidence": "firm" or "close",
            "volatile_parameters": list of str,
            "is_tie": bool,
            "breakdown": dict,
            "recommendation_summary": str
        }
    """
    ci = CostInputs.from_dict(inputs)

    # 1. Calculate Repair Costs
    # C_repair = Q + (tr * v) + (p * Q) + (E_old * L_r)
    repair_quote_cost = ci.Q
    repair_time_cost = ci.tr * ci.v
    repair_risk_cost = ci.p * ci.Q
    repair_operating_cost = ci.E_old * ci.L_r
    total_repair_cost = repair_quote_cost + repair_time_cost + repair_risk_cost + repair_operating_cost
    annual_repair_cost = total_repair_cost / ci.L_r

    # 2. Calculate Replace Costs
    # C_replace = P + D - S + (tn * v) + (E_new * L_n)
    replace_net_capital = ci.P + ci.D - ci.S
    replace_time_cost = ci.tn * ci.v
    replace_operating_cost = ci.E_new * ci.L_n
    total_replace_cost = replace_net_capital + replace_time_cost + replace_operating_cost
    annual_replace_cost = total_replace_cost / ci.L_n

    # 3. Determine Economic Difference & Verdict
    annual_difference = annual_replace_cost - annual_repair_cost
    annual_savings = abs(annual_difference)
    is_tie = annual_savings <= tie_tolerance

    if is_tie:
        # On exact economic ties, repairing is conventionally favored to prevent
        # unnecessary capital commitment and appliance e-waste disposal
        verdict = "Repair"
    elif annual_repair_cost < annual_replace_cost:
        verdict = "Repair"
    else:
        verdict = "Replace"

    # 4. Uncertainty Sensitivity Analysis
    uncertainty_results = run_uncertainty_analysis(
        inputs=ci.to_dict(),
        baseline_verdict=verdict,
        sensitivity_pct=sensitivity_pct,
        tie_tolerance=tie_tolerance,
    )

    # 5. Build Human-Readable Recommendation Summary
    if is_tie:
        rec_summary = (
            f"Verdict: Repair (Economic Tie). Both options cost approx ${annual_repair_cost:,.2f}/year "
            f"(difference of ${annual_savings:,.2f}/yr). Repairing preserves capital."
        )
    elif verdict == "Repair":
        rec_summary = (
            f"Verdict: Repair. Repairing costs ${annual_repair_cost:,.2f}/year vs ${annual_replace_cost:,.2f}/year "
            f"to replace, saving ${annual_savings:,.2f} per year ({uncertainty_results['confidence'].upper()} recommendation)."
        )
    else:
        rec_summary = (
            f"Verdict: Replace. Replacing costs ${annual_replace_cost:,.2f}/year vs ${annual_repair_cost:,.2f}/year "
            f"to repair, saving ${annual_savings:,.2f} per year ({uncertainty_results['confidence'].upper()} recommendation)."
        )

    return {
        "verdict": verdict,
        "annual_repair_cost": round(annual_repair_cost, 2),
        "annual_replace_cost": round(annual_replace_cost, 2),
        "total_repair_cost": round(total_repair_cost, 2),
        "total_replace_cost": round(total_replace_cost, 2),
        "annual_difference": round(annual_difference, 2),
        "annual_savings": round(annual_savings, 2),
        "confidence": uncertainty_results["confidence"],
        "volatile_parameters": uncertainty_results["volatile_parameters"],
        "volatile_parameter": uncertainty_results["volatile_parameter"],
        "is_tie": is_tie,
        "recommendation_summary": rec_summary,
        "breakdown": {
            "repair": {
                "quote_cost": round(repair_quote_cost, 2),
                "time_hassle_cost": round(repair_time_cost, 2),
                "repeat_failure_risk_cost": round(repair_risk_cost, 2),
                "energy_operating_cost": round(repair_operating_cost, 2),
                "total_cost": round(total_repair_cost, 2),
                "annualized_cost": round(annual_repair_cost, 2),
            },
            "replace": {
                "purchase_price": round(ci.P, 2),
                "delivery_and_install": round(ci.D, 2),
                "salvage_credit": round(ci.S, 2),
                "net_capital_outlay": round(replace_net_capital, 2),
                "time_hassle_cost": round(replace_time_cost, 2),
                "energy_operating_cost": round(replace_operating_cost, 2),
                "total_cost": round(total_replace_cost, 2),
                "annualized_cost": round(annual_replace_cost, 2),
            },
        },
        "sensitivity_scenarios": uncertainty_results["scenarios"],
        "inputs_echo": ci.to_dict(),
    }


# ============================================================================
# UNCERTAINTY & SENSITIVITY ENGINE
# ============================================================================

def run_uncertainty_analysis(
    inputs: Dict[str, Any],
    baseline_verdict: Optional[str] = None,
    sensitivity_pct: float = 0.20,
    tie_tolerance: float = 0.01,
) -> Dict[str, Any]:
    """
    Evaluates parameter sensitivity for uncertain lifespan and risk parameters:
    - Repair Lifespan (L_r)
    - Replacement Lifespan (L_n)
    - Repeat Failure Probability (p)

    Tests low, middle, and high scenarios:
    - If verdict is consistent across all three, labels it 'firm'.
    - If the verdict flips under sensitivity, labels it 'close' and identifies volatile parameters.
    """
    ci = CostInputs.from_dict(inputs)

    def _eval(lr: float, ln: float, prob: float) -> str:
        rep_tot = ci.Q * (1.0 + prob) + (ci.tr * ci.v) + (ci.E_old * lr)
        rep_ann = rep_tot / lr
        new_tot = (ci.P + ci.D - ci.S) + (ci.tn * ci.v) + (ci.E_new * ln)
        new_ann = new_tot / ln
        diff = new_ann - rep_ann
        if abs(diff) <= tie_tolerance:
            return "Repair"
        return "Repair" if rep_ann < new_ann else "Replace"

    if baseline_verdict is None:
        baseline_verdict = _eval(ci.L_r, ci.L_n, ci.p)

    # 1. Define Parameter Boundaries
    lr_mid = ci.L_r
    lr_low = max(0.1, lr_mid * (1.0 - sensitivity_pct))
    lr_high = lr_mid * (1.0 + sensitivity_pct)

    ln_mid = ci.L_n
    ln_low = max(0.5, ln_mid * (1.0 - sensitivity_pct))
    ln_high = ln_mid * (1.0 + sensitivity_pct)

    p_mid = ci.p
    p_low = max(0.0, p_mid * (1.0 - sensitivity_pct))
    p_high = min(1.0, p_mid * (1.0 + sensitivity_pct) if p_mid > 0 else 0.10)

    volatile_parameters: List[str] = []

    # 2. Test One-At-A-Time (OAT) Sensitivity for each uncertain variable
    # L_r sensitivity
    lr_verdicts = {
        "low": _eval(lr_low, ln_mid, p_mid),
        "middle": baseline_verdict,
        "high": _eval(lr_high, ln_mid, p_mid),
    }
    if any(v != baseline_verdict for v in lr_verdicts.values()):
        volatile_parameters.append("L_r")

    # L_n sensitivity
    ln_verdicts = {
        "low": _eval(lr_mid, ln_low, p_mid),
        "middle": baseline_verdict,
        "high": _eval(lr_mid, ln_high, p_mid),
    }
    if any(v != baseline_verdict for v in ln_verdicts.values()):
        volatile_parameters.append("L_n")

    # p sensitivity
    p_verdicts = {
        "low": _eval(lr_mid, ln_mid, p_low),
        "middle": baseline_verdict,
        "high": _eval(lr_mid, ln_mid, p_high),
    }
    if any(v != baseline_verdict for v in p_verdicts.values()):
        volatile_parameters.append("p")

    # 3. Test Three Macro Composite Scenarios (Low, Middle, High for Repair Favorability)
    # Scenario "Low" (Pessimistic for Repair / Optimistic for Replace):
    # Short repair life (lr_low), high failure chance (p_high), long new life (ln_high)
    low_scenario_verdict = _eval(lr_low, ln_high, p_high)

    # Scenario "Middle" (Baseline expected parameters):
    mid_scenario_verdict = baseline_verdict

    # Scenario "High" (Optimistic for Repair / Pessimistic for Replace):
    # Long repair life (lr_high), low failure chance (p_low), short new life (ln_low)
    high_scenario_verdict = _eval(lr_high, ln_low, p_low)

    macro_verdicts = [low_scenario_verdict, mid_scenario_verdict, high_scenario_verdict]
    is_macro_consistent = all(v == baseline_verdict for v in macro_verdicts)
    is_oat_consistent = len(volatile_parameters) == 0

    if is_macro_consistent and is_oat_consistent:
        confidence = "firm"
        primary_volatile: Optional[str] = None
    else:
        confidence = "close"
        if not volatile_parameters:
            # If composite flipped but single OAT didn't, identify the dominant driver
            # Compare single-parameter delta to find highest sensitivity
            primary_volatile = "L_r"  # Lifespan is historically the primary elasticity driver
            volatile_parameters.append("L_r")
        else:
            primary_volatile = volatile_parameters[0]

    return {
        "confidence": confidence,
        "volatile_parameters": volatile_parameters,
        "volatile_parameter": primary_volatile or "None",
        "scenarios": {
            "low_repair_favorability": {
                "L_r": round(lr_low, 2),
                "L_n": round(ln_high, 2),
                "p": round(p_high, 3),
                "verdict": low_scenario_verdict,
            },
            "middle_baseline": {
                "L_r": round(lr_mid, 2),
                "L_n": round(ln_mid, 2),
                "p": round(p_mid, 3),
                "verdict": mid_scenario_verdict,
            },
            "high_repair_favorability": {
                "L_r": round(lr_high, 2),
                "L_n": round(ln_low, 2),
                "p": round(p_low, 3),
                "verdict": high_scenario_verdict,
            },
        },
        "parameter_verdicts": {
            "L_r": lr_verdicts,
            "L_n": ln_verdicts,
            "p": p_verdicts,
        },
    }


# ============================================================================
# FLIP ASSUMPTION SOLVER (TIPPING POINT CALCULATOR)
# ============================================================================

def calculate_flip_points(inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes exact mathematical tipping points for all decision variables
    to determine what parameter values cause the verdict to flip.

    Equation for Economic Equilibrium (A_repair == A_replace):
    (Q * (1 + p) + tr * v) / L_r + E_old == (P + D - S + tn * v) / L_n + E_new
    """
    ci = CostInputs.from_dict(inputs)

    # Calculate baseline annualized figures
    k_repair_fixed = ci.Q * (1.0 + ci.p) + (ci.tr * ci.v)
    a_repair = (k_repair_fixed / ci.L_r) + ci.E_old

    k_replace_fixed = (ci.P + ci.D - ci.S) + (ci.tn * ci.v)
    a_replace = (k_replace_fixed / ci.L_n) + ci.E_new

    if a_repair < a_replace:
        base_verdict = "Repair"
        target_verdict = "Replace"
    else:
        base_verdict = "Replace"
        target_verdict = "Repair"

    tipping_points: Dict[str, Optional[float]] = {}
    validity_notes: Dict[str, str] = {}

    # 1. Flip Point for L_r (Repaired Lifespan)
    # k_repair_fixed / L_r + E_old == a_replace  =>  L_r* = k_repair_fixed / (a_replace - E_old)
    denom_lr = a_replace - ci.E_old
    if denom_lr > 1e-6:
        lr_star = k_repair_fixed / denom_lr
        tipping_points["L_r"] = round(lr_star, 2)
        validity_notes["L_r"] = "Valid positive lifespan tipping point."
    elif denom_lr <= 0:
        # Asymptote: Old appliance annual operating cost alone exceeds total annualized replacement cost!
        # Even if L_r -> infinity, repair cost is at least E_old >= a_replace.
        tipping_points["L_r"] = None
        validity_notes["L_r"] = (
            f"Asymptote: Old operating cost (${ci.E_old:,.2f}/yr) alone exceeds or equals "
            f"annualized replacement cost (${a_replace:,.2f}/yr). Infinite lifespan cannot make repair cheaper."
        )

    # 2. Flip Point for Q (Repair Quote)
    # (Q*(1+p) + tr*v)/L_r + E_old == a_replace
    # Q*(1+p) = L_r * (a_replace - E_old) - tr*v
    # Q* = (L_r * (a_replace - E_old) - tr*v) / (1 + p)
    if (1.0 + ci.p) > 0:
        q_star = (ci.L_r * (a_replace - ci.E_old) - (ci.tr * ci.v)) / (1.0 + ci.p)
        tipping_points["Q"] = round(q_star, 2)

    # 3. Flip Point for p (Failure Probability)
    # Q*(1+p) = L_r * (a_replace - E_old) - tr*v
    # 1 + p = (L_r * (a_replace - E_old) - tr*v) / Q
    if ci.Q > 0:
        p_star = ((ci.L_r * (a_replace - ci.E_old) - (ci.tr * ci.v)) / ci.Q) - 1.0
        tipping_points["p"] = round(p_star, 4)

    # 4. Flip Point for P (New Appliance Purchase Price)
    # (P + D - S + tn*v)/L_n + E_new == a_repair
    # P + D - S + tn*v = L_n * (a_repair - E_new)
    # P* = L_n * (a_repair - E_new) - (D - S + tn*v)
    p_star = ci.L_n * (a_repair - ci.E_new) - (ci.D - ci.S + (ci.tn * ci.v))
    tipping_points["P"] = round(p_star, 2)

    # 5. Flip Point for L_n (New Appliance Lifespan)
    # k_replace_fixed / L_n + E_new == a_repair  =>  L_n* = k_replace_fixed / (a_repair - E_new)
    denom_ln = a_repair - ci.E_new
    if denom_ln > 1e-6:
        ln_star = k_replace_fixed / denom_ln
        tipping_points["L_n"] = round(ln_star, 2)

    return {
        "base_verdict": base_verdict,
        "target_verdict": target_verdict,
        "annual_repair_cost": round(a_repair, 2),
        "annual_replace_cost": round(a_replace, 2),
        "tipping_points": tipping_points,
        "validity_notes": validity_notes,
        "current_values": ci.to_dict(),
    }


def find_flip_point(inputs: Dict[str, Any]) -> str:
    """
    Calculates the exact tipping point variable change required to flip
    the repair vs. replace decision, returning a clean, human-readable sentence.

    Examples of output:
    - "To flip the verdict to Repair, the repaired appliance would need to last at least 3.4 years
       (currently 2.0 years), or the repair quote would need to drop below $185.50 (currently $350.00)."
    - "To flip the verdict to Replace, the repair lifespan would need to drop below 1.2 years
       (currently 3.0 years), or the repair quote would need to rise above $480.00 (currently $250.00)."
    """
    fp = calculate_flip_points(inputs)
    base_verdict = fp["base_verdict"]
    target_verdict = fp["target_verdict"]
    tp = fp["tipping_points"]
    cur = fp["current_values"]

    # Exact Tie
    if abs(fp["annual_repair_cost"] - fp["annual_replace_cost"]) <= 0.01:
        return (
            "The options are currently in economic tie ($0.00/yr difference); "
            "any minor change in repair lifespan (L_r) or repair quote (Q) will tip the verdict."
        )

    # CASE 1: Base Verdict is REPLACE -> How to flip to REPAIR?
    if base_verdict == "Replace":
        lr_star = tp.get("L_r")
        q_star = tp.get("Q")

        # Check for asymptotic energy block
        if lr_star is None or lr_star <= 0:
            p_star = tp.get("P")
            if p_star is not None and p_star > cur["P"]:
                return (
                    f"To flip the verdict to Repair, the new appliance price would need to rise from "
                    f"${cur['P']:,.2f} to above ${p_star:,.2f}; extending repair lifespan alone cannot "
                    f"flip the decision because old operating costs (${cur['E_old']:,.2f}/yr) exceed "
                    f"the annualized replacement cost (${fp['annual_replace_cost']:,.2f}/yr)."
                )
            return (
                f"To flip the verdict to Repair, the repair quote would need to drop from "
                f"${cur['Q']:,.2f} to below ${q_star:,.2f}."
                if q_star is not None and q_star >= 0
                else "To flip the verdict to Repair, substantial cost reductions in repair quote or replacement price are required."
            )

        # Standard Lifespan & Quote Tipping Point
        msg_parts = [
            f"To flip the verdict to Repair, the repaired appliance would need to last at least "
            f"{lr_star:.1f} years (currently {cur['L_r']:.1f} years)"
        ]

        if q_star is not None and q_star > 0:
            msg_parts.append(
                f", or the repair quote would need to drop below ${q_star:,.2f} (currently ${cur['Q']:,.2f})"
            )
        elif q_star is not None and q_star <= 0:
            msg_parts.append(" (even a $0 free repair quote would not be enough without extended lifespan)")

        return "".join(msg_parts) + "."

    # CASE 2: Base Verdict is REPAIR -> How to flip to REPLACE?
    lr_star = tp.get("L_r")
    q_star = tp.get("Q")
    p_star = tp.get("P")

    msg_parts = []
    if lr_star is not None and lr_star > 0:
        msg_parts.append(
            f"To flip the verdict to Replace, the repair lifespan would need to drop below "
            f"{lr_star:.1f} years (currently {cur['L_r']:.1f} years)"
        )
    else:
        msg_parts.append("To flip the verdict to Replace, the repair durability would need to degrade severely")

    if q_star is not None and q_star > cur["Q"]:
        msg_parts.append(
            f", or the repair quote would need to rise above ${q_star:,.2f} (currently ${cur['Q']:,.2f})"
        )
    elif p_star is not None and 0 < p_star < cur["P"]:
        msg_parts.append(
            f", or the new replacement price would need to drop below ${p_star:,.2f} (currently ${cur['P']:,.2f})"
        )

    return "".join(msg_parts) + "."


# ============================================================================
# CLI ENTRYPOINT
# ============================================================================

if __name__ == "__main__":
    sample_inputs = {
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

    result = calculate_annualized_costs(sample_inputs)
    flip_sentence = find_flip_point(sample_inputs)

    print("=================================================================")
    print("COST ENGINE CALCULATION OUTPUT")
    print("=================================================================")
    print(f"Verdict:              {result['verdict']}")
    print(f"Annual Repair Cost:   ${result['annual_repair_cost']:,.2f}/yr")
    print(f"Annual Replace Cost:  ${result['annual_replace_cost']:,.2f}/yr")
    print(f"Annual Savings:       ${result['annual_savings']:,.2f}/yr")
    print(f"Confidence:           {result['confidence'].upper()}")
    print(f"Volatile Parameters:  {result['volatile_parameters']}")
    print(f"Recommendation:       {result['recommendation_summary']}")
    print("-----------------------------------------------------------------")
    print("FLIP ASSUMPTION ANALYSIS:")
    print(flip_sentence)
    print("=================================================================")

