"""
repair_replace_advisor.py
=========================
Production End-to-End Orchestrator for the Repair or Replace Advisor.

Bridges:
1. Appliance Diagnostic Triage (from `appliance_inference.py` / Adaption fine-tuned model)
   - Estimates repair quote range (Q)
   - Estimates extended repair lifespan (L_r)
   - Estimates repeat breakdown risk (p)
2. Deterministic Financial Decision Engine (from `cost_engine.py`)
   - Guarantees the Language Model NEVER performs math
   - Computes annualized costs (A_repair, A_replace), net differences, and savings
   - Runs sensitivity scenarios (firm vs. close confidence)
   - Computes tipping points (find_flip_point)
3. Structured Consumer Advisory Report Generation
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Union

try:
    from backend.appliance_inference import (
        ApplianceDiagnosisEngine,
        DiagnosticRequest,
        DiagnosticResponse,
    )
    from backend.cost_engine import (
        calculate_annualized_costs,
        calculate_flip_points,
        find_flip_point,
    )
except ImportError:
    from appliance_inference import (
        ApplianceDiagnosisEngine,
        DiagnosticRequest,
        DiagnosticResponse,
    )
    from cost_engine import (
        calculate_annualized_costs,
        calculate_flip_points,
        find_flip_point,
    )

logger = logging.getLogger("repair_replace_advisor")
if not logger.handlers:
    _h = logging.StreamHandler(sys.stdout)
    _h.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [repair_replace_advisor] %(message)s")
    )
    logger.addHandler(_h)
logger.setLevel(logging.INFO)


# Typical baseline market defaults for Indian domestic appliances
APPLIANCE_MARKET_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Washing Machine": {
        "P": 28000.0,       # Avg new front/top load price (₹)
        "D": 800.0,         # Delivery/installation
        "S": 1500.0,        # Scrap/trade-in credit
        "L_n": 10.0,        # New machine lifespan (years)
        "E_new": 1800.0,    # 5-star inverter energy (₹/yr)
        "E_old": 3200.0,    # Older machine energy (₹/yr)
        "tn": 4.0,          # 4 hours shopping/delivery
        "tr": 5.0,          # 5 hours technician coordination
        "v": 350.0,         # Default hourly time value (₹/hr)
    },
    "Air Conditioner": {
        "P": 38000.0,       # 1.5T 3-Star/5-Star Inverter AC (₹)
        "D": 1800.0,        # Installation + piping
        "S": 2500.0,        # Buyback for outdoor/indoor unit
        "L_n": 8.0,         # Lifespan
        "E_new": 6500.0,    # Annual power consumption
        "E_old": 11500.0,   # Older non-inverter power
        "tn": 5.0,
        "tr": 6.0,
        "v": 350.0,
    },
    "Refrigerator": {
        "P": 26000.0,       # Double Door Frost Free (₹)
        "D": 600.0,
        "S": 1800.0,
        "L_n": 10.0,
        "E_new": 1600.0,
        "E_old": 3400.0,
        "tn": 3.0,
        "tr": 4.0,
        "v": 350.0,
    },
    "Water Purifier": {
        "P": 16000.0,       # RO+UV+UF Minerals
        "D": 400.0,
        "S": 500.0,
        "L_n": 6.0,
        "E_new": 600.0,
        "E_old": 900.0,
        "tn": 2.0,
        "tr": 3.0,
        "v": 350.0,
    },
    "Water Heater": {
        "P": 9500.0,        # 15L-25L 5-star storage geyser
        "D": 500.0,
        "S": 400.0,
        "L_n": 7.0,
        "E_new": 2200.0,
        "E_old": 3500.0,
        "tn": 2.0,
        "tr": 3.0,
        "v": 350.0,
    },
}


@dataclass
class AdvisorCaseRequest:
    """User input payload for end-to-end evaluation."""

    brand: str
    appliance_type: str
    symptom_description: str
    error_code: Optional[str] = None
    model_number: Optional[str] = None
    user_time_value_hourly: Optional[float] = None
    repair_quote_override: Optional[float] = None
    expected_repair_lifespan_override: Optional[float] = None
    user_financial_inputs: Dict[str, float] = field(default_factory=dict)


@dataclass
class AdvisorComprehensiveReport:
    """Consolidated diagnostic and financial decision report."""

    case_id: str
    brand: str
    appliance_type: str
    diagnostic_summary: str
    triage_level: str
    safety_alerts: List[str]
    probable_root_causes: List[str]
    step_by_step_triage: List[str]
    verdict: str  # 'Repair' or 'Replace'
    confidence: str  # 'firm' or 'close'
    volatile_parameters: List[str]
    annual_repair_cost: float
    annual_replace_cost: float
    annual_savings: float
    total_repair_cost: float
    total_replace_cost: float
    tipping_point_analysis: str
    cost_breakdown: Dict[str, Any]
    actionable_next_steps: List[str]

    def render_markdown(self) -> str:
        """Renders report in publication-ready GitHub-flavored Markdown."""
        verdict_badge = "🔧 **RECOMMENDATION: REPAIR**" if self.verdict == "Repair" else "🛒 **RECOMMENDATION: REPLACE**"
        confidence_badge = f"*{self.confidence.upper()} CONFIDENCE*"
        
        safety_section = ""
        if self.safety_alerts:
            safety_section = "\n> [!CAUTION]\n> " + "\n> ".join(self.safety_alerts) + "\n"

        causes_bullets = "\n".join(f"- {c}" for c in self.probable_root_causes)
        steps_bullets = "\n".join(f"1. {s}" for s in self.step_by_step_triage)
        next_steps = "\n".join(f"- {ns}" for ns in self.actionable_next_steps)

        return f"""# Repair or Replace Advisory Report: {self.brand} {self.appliance_type}

{safety_section}

## 1. Executive Decision
### {verdict_badge} ({confidence_badge})

> {self.diagnostic_summary}

| Economic Metric | Repair Option | Replacement Option | Net Variance |
| :--- | :---: | :---: | :---: |
| **Annualized Cost** | **₹{self.annual_repair_cost:,.2f}/yr** | **₹{self.annual_replace_cost:,.2f}/yr** | **₹{self.annual_savings:,.2f}/yr saved** |
| **Total Cumulative Cost** | ₹{self.total_repair_cost:,.2f} | ₹{self.total_replace_cost:,.2f} | Lifecycle Total |
| **Triage Classification** | `{self.triage_level}` | Capital Outlay | — |

---

## 2. Technical Diagnostic Breakdown
**Probable Root Causes:**
{causes_bullets}

**Step-by-Step Triage & Verification:**
{steps_bullets}

---

## 3. Financial Modeling & Flip Assumption
All financial calculations were computed deterministically via `cost_engine.py`.

- **Decision Confidence:** `{self.confidence.upper()}`
- **Volatile Parameters (Sensitivity Drivers):** `{self.volatile_parameters or 'None'}`
- **Tipping Point (Flip Assumption):**  
  *{self.tipping_point_analysis}*

---

## 4. Actionable Next Steps
{next_steps}

*Report generated deterministically by Repair or Replace Advisor.*
"""


class RepairReplaceAdvisor:
    """
    Coordinator tying diagnostic intelligence to deterministic financial modeling.
    """

    def __init__(self, diagnosis_engine: Optional[ApplianceDiagnosisEngine] = None):
        self.diag_engine = diagnosis_engine or ApplianceDiagnosisEngine()

    def evaluate_case(self, case: AdvisorCaseRequest) -> AdvisorComprehensiveReport:
        logger.info(
            "Evaluating Repair or Replace case for %s %s: '%s'...",
            case.brand,
            case.appliance_type,
            case.symptom_description[:50],
        )

        # Step 1: Run AI Diagnostic Inference
        diag_req = DiagnosticRequest(
            appliance_type=case.appliance_type,
            symptom_description=case.symptom_description,
            brand=case.brand,
            model_number=case.model_number,
            error_code=case.error_code,
        )
        diag_resp: DiagnosticResponse = self.diag_engine.diagnose(diag_req)

        # Step 2: Assemble Financial Inputs
        financial_inputs = self._synthesize_financial_inputs(case, diag_resp)

        # Step 3: Execute Deterministic Financial Calculations (NO MATH IN LLM)
        cost_results = calculate_annualized_costs(financial_inputs)
        flip_sentence = find_flip_point(financial_inputs)

        # Step 4: Determine Actionable Guidance
        actionable_steps = self._formulate_next_steps(
            diag_resp=diag_resp,
            cost_results=cost_results,
            brand=case.brand,
            appliance=case.appliance_type,
        )

        case_id = f"ADV_{case.brand[:3].upper()}_{diag_resp.model_identifier.split('-')[-1]}"

        return AdvisorComprehensiveReport(
            case_id=case_id,
            brand=case.brand,
            appliance_type=case.appliance_type,
            diagnostic_summary=diag_resp.summary,
            triage_level=diag_resp.triage_level,
            safety_alerts=diag_resp.safety_precautions,
            probable_root_causes=diag_resp.probable_causes,
            step_by_step_triage=diag_resp.step_by_step_triage,
            verdict=cost_results["verdict"],
            confidence=cost_results["confidence"],
            volatile_parameters=cost_results["volatile_parameters"],
            annual_repair_cost=cost_results["annual_repair_cost"],
            annual_replace_cost=cost_results["annual_replace_cost"],
            annual_savings=cost_results["annual_savings"],
            total_repair_cost=cost_results["total_repair_cost"],
            total_replace_cost=cost_results["total_replace_cost"],
            tipping_point_analysis=flip_sentence,
            cost_breakdown=cost_results["breakdown"],
            actionable_next_steps=actionable_steps,
        )

    def _synthesize_financial_inputs(
        self, case: AdvisorCaseRequest, diag: DiagnosticResponse
    ) -> Dict[str, float]:
        """Merges market defaults, diagnostic severity estimates, and user overrides."""
        market = copy_defaults = dict(
            APPLIANCE_MARKET_DEFAULTS.get(
                case.appliance_type, APPLIANCE_MARKET_DEFAULTS["Washing Machine"]
            )
        )

        # User time value
        v = case.user_time_value_hourly or market["v"]

        # Estimate Repair Quote Q based on triage severity if not provided
        if case.repair_quote_override is not None:
            Q = case.repair_quote_override
        elif diag.triage_level == "EMERGENCY" or "compressor" in diag.raw_response.lower():
            Q = market["P"] * 0.35  # Major 35% component repair
        elif diag.triage_level == "TECHNICIAN_MANDATORY":
            Q = market["P"] * 0.22  # Specialized repair
        elif diag.triage_level == "ASSISTED_DIY":
            Q = market["P"] * 0.10  # Moderate part replacement
        else:
            Q = market["P"] * 0.04  # Minor filter/latch DIY fix

        # Extended repair lifespan L_r
        if case.expected_repair_lifespan_override is not None:
            L_r = case.expected_repair_lifespan_override
        elif diag.triage_level in ("TECHNICIAN_MANDATORY", "EMERGENCY"):
            L_r = 1.5  # Heavy component repair usually yields 1.5 years
        else:
            L_r = 3.0  # Minor repair yields 3 years

        # Repeat failure probability p
        p = 0.30 if diag.triage_level in ("TECHNICIAN_MANDATORY", "EMERGENCY") else 0.10

        merged = {
            "Q": float(Q),
            "tr": float(market["tr"]),
            "tn": float(market["tn"]),
            "v": float(v),
            "p": float(p),
            "E_old": float(market["E_old"]),
            "E_new": float(market["E_new"]),
            "L_r": float(L_r),
            "L_n": float(market["L_n"]),
            "P": float(market["P"]),
            "D": float(market["D"]),
            "S": float(market["S"]),
        }

        # Apply explicit user financial overrides
        for k, val in case.user_financial_inputs.items():
            merged[k] = float(val)

        return merged

    def _formulate_next_steps(
        self,
        diag_resp: DiagnosticResponse,
        cost_results: Dict[str, Any],
        brand: str,
        appliance: str,
    ) -> List[str]:
        steps = []
        if diag_resp.safety_precautions:
            steps.append("Isolate power immediately before touching any internal wiring or wet surfaces.")

        if cost_results["verdict"] == "Repair":
            steps.append(
                f"Obtain a binding service estimate from an authorized {brand} service center."
            )
            steps.append(
                "If the technician's written quote exceeds the tipping point, halt repair and switch to replacement."
            )
            steps.append("Verify if replacement parts include a minimum 90-day manufacturer warranty.")
        else:
            steps.append(
                f"Browse modern 5-star inverter replacement models for {appliance} to capture energy rebates."
            )
            steps.append(
                "Request dealer scrap/buyback exchange value for the existing decommissioned appliance."
            )
            steps.append("Do not spend any diagnostic call-out fee or component deposit on the old appliance.")

        return steps


if __name__ == "__main__":
    advisor = RepairReplaceAdvisor()
    sample_case = AdvisorCaseRequest(
        brand="IFB",
        appliance_type="Washing Machine",
        symptom_description="Bhaiya wash cycle start karne pe dE error display pe aa raha hai aur continuous beep ho rahi hai",
        error_code="dE",
        repair_quote_override=2400.0,
    )

    report = advisor.evaluate_case(sample_case)
    print(report.render_markdown())

