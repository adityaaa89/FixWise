"""
schemas.py
==========
Pydantic Request & Response Schemas for the Repair or Replace Advisor API.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ============================================================================
# DIAGNOSIS SCHEMAS
# ============================================================================

class DiagnoseRequest(BaseModel):
    appliance_type: str = Field(..., example="Washing Machine", description="Category of appliance")
    brand: str = Field(..., example="IFB", description="Appliance manufacturer/brand")
    age: float = Field(..., ge=0.0, example=4.5, description="Appliance age in years")
    symptom_text: str = Field(..., example="Machine beeping with dE error code on spin cycle", description="Customer symptom description")
    model: Optional[str] = Field(None, example="Senator Smart Touch", description="Appliance model number/name")
    error_code: Optional[str] = Field(None, example="dE", description="Diagnostic error code if displayed")
    case_id: Optional[str] = Field(None, description="Optional existing case ID to link")


class RankedCause(BaseModel):
    rank: int
    cause: str
    technical_description: str
    part_category: str
    diy_difficulty: str  # 'Easy DIY', 'Moderate DIY', 'Technician Required', 'Specialist/Hazard'
    cost_band: Dict[str, float]  # {'low': 800.0, 'high': 1500.0}
    estimated_labor_hours: float
    probability_score: float


class DiagnoseResponse(BaseModel):
    case_id: str
    appliance_type: str
    brand: str
    age_assessment: str
    triage_level: str
    safety_alerts: List[str]
    ranked_causes: List[RankedCause]
    reference_benchmark: Optional[Dict[str, Any]] = None
    source: str = "adaption_model"  # 'adaption_model' or 'fallback_retriever'


# ============================================================================
# QUOTE CHECK SCHEMAS
# ============================================================================

class QuoteCheckRequest(BaseModel):
    appliance_category: str = Field(..., example="Washing Machine")
    part_category: str = Field(..., example="Drain Pump")
    quoted_part_price: float = Field(..., ge=0.0, example=2200.0, description="Quoted part cost ($ or ₹)")
    quoted_labor_price: Optional[float] = Field(None, ge=0.0, example=600.0, description="Quoted technician labor ($ or ₹)")
    quoted_total_price: Optional[float] = Field(None, ge=0.0, description="Optional combined total quote ($ or ₹)")
    estimated_labor_hours: Optional[float] = Field(None, ge=0.0, description="Technician estimated hours on site")


class QuoteCheckResponse(BaseModel):
    appliance_category: str
    part_category: str
    part_status: str  # 'fair', 'inflated', 'unusually_low', 'unknown'
    labor_status: str  # 'fair', 'inflated', 'unusually_low', 'unknown'
    overall_status: str  # 'reasonable', 'inflated', 'unusually_low', 'warning'
    benchmarks: Dict[str, Any]
    variance: Dict[str, Any]
    advisory_notes: List[str]


# ============================================================================
# VERDICT SCHEMAS
# ============================================================================

class VerdictRequest(BaseModel):
    case_id: Optional[str] = Field(None, description="Optional case ID to update")
    Q: float = Field(..., ge=0.0, description="Repair quote / parts & labor cost ($ or ₹)")
    tr: float = Field(..., ge=0.0, description="Time lost / hassle hours waiting for repair")
    tn: float = Field(..., ge=0.0, description="Time lost / hassle hours ordering & installing replacement")
    v: float = Field(..., ge=0.0, description="Monetary value of consumer's time ($/hr or ₹/hr)")
    p: float = Field(..., ge=0.0, le=1.0, description="Probability of repeat breakdown (0.0 to 1.0)")
    E_old: float = Field(..., ge=0.0, description="Annual energy / operating cost of old appliance")
    E_new: float = Field(..., ge=0.0, description="Annual energy / operating cost of new appliance")
    L_r: float = Field(..., gt=0.0, description="Expected extended repair lifespan (strictly > 0 years)")
    L_n: float = Field(..., gt=0.0, description="Expected replacement lifespan (strictly > 0 years)")
    P: float = Field(..., ge=0.0, description="Purchase price of brand-new replacement")
    D: float = Field(0.0, ge=0.0, description="Delivery and installation fee")
    S: float = Field(0.0, ge=0.0, description="Salvage or scrap rebate credit")
    sensitivity_pct: float = Field(0.20, gt=0.0, lt=1.0, description="Sensitivity variation factor (default 20%)")


class VerdictResponse(BaseModel):
    case_id: Optional[str]
    verdict: str  # 'Repair' or 'Replace'
    confidence: str  # 'firm' or 'close'
    volatile_parameters: List[str]
    volatile_parameter: str
    annual_repair_cost: float
    annual_replace_cost: float
    annual_savings: float
    total_repair_cost: float
    total_replace_cost: float
    annual_difference: float
    is_tie: bool
    flip_assumption: str
    tipping_points: Dict[str, Any]
    breakdown: Dict[str, Any]
    recommendation_summary: str


# ============================================================================
# PHOTO EXTRACTION SCHEMAS
# ============================================================================

class PhotoExtractionResponse(BaseModel):
    brand: str
    model_number: str
    serial_number: Optional[str] = None
    appliance_type: Optional[str] = None
    electrical_specs: Dict[str, Any] = Field(default_factory=dict)
    detected_error_codes: List[str] = Field(default_factory=list)
    confidence_score: float
    raw_extracted_text: str
    advisory_tip: str


# ============================================================================
# CASE RETRIEVAL SCHEMAS
# ============================================================================

class CaseResponse(BaseModel):
    id: str
    created_at: str
    updated_at: str
    user_input_snapshot: Dict[str, Any]
    returned_diagnosis: Optional[Dict[str, Any]] = None
    cost_parameters: Optional[Dict[str, Any]] = None
    final_verdict: Optional[Dict[str, Any]] = None

