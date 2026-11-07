"""
main.py
=======
FastAPI Backend Application for the Repair or Replace Advisor.

Core Architecture:
1. Database Layer: SQLAlchemy with SQLite persistence for:
   - appliance_reference
   - part_price_bands
   - cases
2. REST API Endpoints:
   - POST /api/diagnose   : AI diagnosis with fallback retriever, age assessment, and part cost bands
   - POST /api/quote-check: Benchmarks repair quotes against part price bands to flag inflation
   - POST /api/verdict    : Deterministic cost engine execution (annualized costs, flip point, sensitivity)
   - POST /api/photo      : Vision LLM rating plate sticker analysis
   - GET  /api/cases/{id} : Retrieves historical case assessment snapshots
"""

from __future__ import annotations

import contextlib
import datetime
import json
import logging
import os
import sys
import uuid
from typing import Any, Dict, List, Optional, Tuple

# Ensure both backend dir and project root are in sys.path
_cur_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_cur_dir)
for _p in [_cur_dir, _root_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Ensure both backend dir and project root are in sys.path
_cur_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_cur_dir)
for _p in [_cur_dir, _root_dir]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

def _load_env_file() -> None:
    """Zero-dependency .env loader ensuring environment variables are populated."""
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(cur_dir), ".env"),
        os.path.join(cur_dir, ".env"),
    ]
    for env_path in candidates:
        if os.path.exists(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip('"').strip("'")
                            if k and k not in os.environ:
                                os.environ[k] = v
            except Exception:
                pass

_load_env_file()

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, text
from sqlalchemy.orm import Session

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
    from backend.database import Base, SessionLocal, engine, get_db
    from backend.models import ApplianceReference, CaseRecord, PartPriceBand
    from backend.schemas import (
        CaseResponse,
        DiagnoseRequest,
        DiagnoseResponse,
        PhotoExtractionResponse,
        QuoteCheckRequest,
        QuoteCheckResponse,
        RankedCause,
        VerdictRequest,
        VerdictResponse,
    )
    from backend.vision_client import ApplianceVisionClient
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
    from database import Base, SessionLocal, engine, get_db
    from models import ApplianceReference, CaseRecord, PartPriceBand
    from schemas import (
        CaseResponse,
        DiagnoseRequest,
        DiagnoseResponse,
        PhotoExtractionResponse,
        QuoteCheckRequest,
        QuoteCheckResponse,
        RankedCause,
        VerdictRequest,
        VerdictResponse,
    )
    from vision_client import ApplianceVisionClient

# ============================================================================
# LOGGING SETUP
# ============================================================================

logger = logging.getLogger("advisor_backend")
if not logger.handlers:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(
        logging.Formatter("[%(asctime)s] [%(levelname)s] [main] %(message)s")
    )
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


# ============================================================================
# DATABASE SEEDING
# ============================================================================

def seed_database_defaults(db: Session) -> None:
    """Pre-populates baseline appliance references and part price bands if tables are empty."""
    # 1. Seed Appliance References
    if db.query(ApplianceReference).count() == 0:
        logger.info("Seeding baseline appliance reference data...")
        references = [
            ApplianceReference(
                appliance_type="Washing Machine",
                baseline_lifespan=10.0,
                typical_yearly_running_cost=2400.0,
                common_failure_list=[
                    "Door lock latch error (dE)",
                    "Drain pump filter clogged with lint/coins (E03 / 5E)",
                    "Inlet water valve timeout (tAP / 4E)",
                    "Drum unbalanced spin cycle / shock absorber wear (unb)",
                    "Motor run capacitor or drive belt slipped",
                ],
            ),
            ApplianceReference(
                appliance_type="Air Conditioner",
                baseline_lifespan=8.0,
                typical_yearly_running_cost=8500.0,
                common_failure_list=[
                    "Indoor fan blower feedback motor error (E4)",
                    "Refrigerant leak / evaporator sensor low temp (EC)",
                    "Outdoor IPM inverter driver board overcurrent (F1)",
                    "Condensate drain line choking causing indoor water drip",
                    "PCB optical coupler damaged by voltage surge",
                ],
            ),
            ApplianceReference(
                appliance_type="Refrigerator",
                baseline_lifespan=10.0,
                typical_yearly_running_cost=2200.0,
                common_failure_list=[
                    "Compressor PTC starter relay burn (ticking click sound)",
                    "Defrost bi-metal thermostat failure / freezer ice mountain",
                    "Evaporator duct choked with frost blocking fridge airflow",
                    "Defrost drain hole clogged causing bottom water leak",
                    "Inverter compressor PCB driver fault (error 22)",
                ],
            ),
            ApplianceReference(
                appliance_type="Water Purifier",
                baseline_lifespan=6.0,
                typical_yearly_running_cost=1200.0,
                common_failure_list=[
                    "UV lamp filament burned / continuous beep alarm",
                    "RO membrane scaling / high TDS rejection drop",
                    "Booster pump head pressure failure",
                    "Spun polypropylene pre-filter sedimentation choking",
                    "Solenoid valve stuck shut",
                ],
            ),
            ApplianceReference(
                appliance_type="Water Heater",
                baseline_lifespan=7.0,
                typical_yearly_running_cost=2800.0,
                common_failure_list=[
                    "Incoloy heating element sheath scale puncture (MCB trip)",
                    "Capillary thermostat cut-out stuck open",
                    "Magnesium sacrificial anode rod exhaustion",
                    "Pressure relief safety valve dripping / scale lock",
                ],
            ),
            ApplianceReference(
                appliance_type="Microwave Oven",
                baseline_lifespan=8.0,
                typical_yearly_running_cost=750.0,
                common_failure_list=[
                    "High voltage diode or capacitor short (loud hum, no heat)",
                    "Magnetron vacuum filament exhaustion",
                    "Door interlock microswitch misaligned",
                    "Turntable synchronous motor gear stripped",
                ],
            ),
        ]
        db.add_all(references)
        db.commit()

    # 2. Seed Part Price Bands
    if db.query(PartPriceBand).count() == 0:
        logger.info("Seeding part price bands benchmark data...")
        bands = [
            # Washing Machine Parts
            PartPriceBand(
                appliance_category="Washing Machine",
                part_category="Drain Pump",
                low_price_threshold=1100.0,
                high_price_threshold=2200.0,
                typical_labor_hours=1.0,
                typical_labor_rate_hourly=400.0,
                notes="OEM synchronous magnetic drain pump. High end covers front loaders.",
            ),
            PartPriceBand(
                appliance_category="Washing Machine",
                part_category="Door Lock Assembly",
                low_price_threshold=650.0,
                high_price_threshold=1500.0,
                typical_labor_hours=0.8,
                typical_labor_rate_hourly=400.0,
                notes="PTC thermal actuator or solenoid latch microswitch.",
            ),
            PartPriceBand(
                appliance_category="Washing Machine",
                part_category="Water Inlet Solenoid Valve",
                low_price_threshold=550.0,
                high_price_threshold=1300.0,
                typical_labor_hours=0.8,
                typical_labor_rate_hourly=400.0,
                notes="Dual / triple solenoid 230V valve coil assembly.",
            ),
            PartPriceBand(
                appliance_category="Washing Machine",
                part_category="Main Inverter PCB Board",
                low_price_threshold=3200.0,
                high_price_threshold=6500.0,
                typical_labor_hours=1.5,
                typical_labor_rate_hourly=500.0,
                notes="Primary microcontroller & inverter motor drive motherboard.",
            ),
            PartPriceBand(
                appliance_category="Washing Machine",
                part_category="Drum Shock Absorber Set",
                low_price_threshold=900.0,
                high_price_threshold=1900.0,
                typical_labor_hours=1.5,
                typical_labor_rate_hourly=450.0,
                notes="Pair of hydraulic friction dampers for front load tub.",
            ),
            # Air Conditioner Parts
            PartPriceBand(
                appliance_category="Air Conditioner",
                part_category="Outdoor Compressor",
                low_price_threshold=6500.0,
                high_price_threshold=13500.0,
                typical_labor_hours=3.0,
                typical_labor_rate_hourly=600.0,
                notes="Twin rotary inverter compressor (excluding nitrogen flush & gas).",
            ),
            PartPriceBand(
                appliance_category="Air Conditioner",
                part_category="Inverter Driver PCB Board",
                low_price_threshold=3800.0,
                high_price_threshold=7800.0,
                typical_labor_hours=1.5,
                typical_labor_rate_hourly=500.0,
                notes="Outdoor unit IPM heat sink power board.",
            ),
            PartPriceBand(
                appliance_category="Air Conditioner",
                part_category="Indoor Fan Blower Motor",
                low_price_threshold=1600.0,
                high_price_threshold=3400.0,
                typical_labor_hours=1.5,
                typical_labor_rate_hourly=450.0,
                notes="BLDC / PG feedback indoor cross-flow fan motor.",
            ),
            PartPriceBand(
                appliance_category="Air Conditioner",
                part_category="Refrigerant Gas Leak Repair & Recharge",
                low_price_threshold=2200.0,
                high_price_threshold=3900.0,
                typical_labor_hours=2.0,
                typical_labor_rate_hourly=500.0,
                notes="U-bend brazing, vacuum to 500 microns, and weighed R32/R410A charge.",
            ),
            PartPriceBand(
                appliance_category="Air Conditioner",
                part_category="Evaporator Sensor Thermistor",
                low_price_threshold=350.0,
                high_price_threshold=850.0,
                typical_labor_hours=0.8,
                typical_labor_rate_hourly=350.0,
                notes="Copper/epoxy 10k or 15k Ohm temperature sensor.",
            ),
            # Refrigerator Parts
            PartPriceBand(
                appliance_category="Refrigerator",
                part_category="PTC Starter Relay & Overload Protector",
                low_price_threshold=350.0,
                high_price_threshold=850.0,
                typical_labor_hours=0.5,
                typical_labor_rate_hourly=350.0,
                notes="Ceramic starter disc relay and thermal bimetal OLP.",
            ),
            PartPriceBand(
                appliance_category="Refrigerator",
                part_category="Defrost Bi-Metal & Heater Assembly",
                low_price_threshold=850.0,
                high_price_threshold=1900.0,
                typical_labor_hours=1.2,
                typical_labor_rate_hourly=400.0,
                notes="Quartz tube / aluminum defrost heater plus defrost thermostat.",
            ),
            PartPriceBand(
                appliance_category="Refrigerator",
                part_category="Inverter Refrigerator Compressor",
                low_price_threshold=5200.0,
                high_price_threshold=9500.0,
                typical_labor_hours=2.5,
                typical_labor_rate_hourly=550.0,
                notes="Variable speed inverter linear/rotary compressor.",
            ),
            PartPriceBand(
                appliance_category="Refrigerator",
                part_category="Evaporator Fan Motor",
                low_price_threshold=950.0,
                high_price_threshold=2100.0,
                typical_labor_hours=1.0,
                typical_labor_rate_hourly=400.0,
                notes="DC 12V/24V brushless freezer air circulation motor.",
            ),
            # Water Purifier Parts
            PartPriceBand(
                appliance_category="Water Purifier",
                part_category="RO Membrane",
                low_price_threshold=1400.0,
                high_price_threshold=2800.0,
                typical_labor_hours=0.8,
                typical_labor_rate_hourly=350.0,
                notes="75 GPD / 100 GPD thin film composite (TFC) spiral wound membrane.",
            ),
            PartPriceBand(
                appliance_category="Water Purifier",
                part_category="UV Lamp & SMPS Ballast",
                low_price_threshold=800.0,
                high_price_threshold=1600.0,
                typical_labor_hours=0.8,
                typical_labor_rate_hourly=350.0,
                notes="11W Phillips/Kent UV tube with 24V electronic ballast.",
            ),
            PartPriceBand(
                appliance_category="Water Purifier",
                part_category="Booster Pump",
                low_price_threshold=1700.0,
                high_price_threshold=3200.0,
                typical_labor_hours=1.0,
                typical_labor_rate_hourly=400.0,
                notes="Diaphragm DC 24V/48V 100 GPD pressure booster pump.",
            ),
            # Water Heater Parts
            PartPriceBand(
                appliance_category="Water Heater",
                part_category="Incoloy Heating Element",
                low_price_threshold=900.0,
                high_price_threshold=1900.0,
                typical_labor_hours=1.2,
                typical_labor_rate_hourly=400.0,
                notes="2000W / 3000W Incoloy 800 scale-resistant heating element.",
            ),
            PartPriceBand(
                appliance_category="Water Heater",
                part_category="Capillary Thermostat & Thermal Cutout",
                low_price_threshold=550.0,
                high_price_threshold=1150.0,
                typical_labor_hours=0.8,
                typical_labor_rate_hourly=350.0,
                notes="Dual stem preset safety cutout and adjustable thermostat.",
            ),
        ]
        db.add_all(bands)
        db.commit()


# ============================================================================
# LIFESPAN & APPLICATION INITIALIZATION
# ============================================================================

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes tables and seeds reference data upon server startup."""
    logger.info("Initializing SQLite database tables...")
    Base.metadata.create_all(bind=engine)
    
    with SessionLocal() as db:
        seed_database_defaults(db)
        
    logger.info("Database initialized successfully.")
    yield
    logger.info("Shutting down Repair or Replace Advisor backend.")


app = FastAPI(
    title="Repair or Replace Advisor API",
    version="2.0.0",
    description=(
        "Production backend service for appliance diagnosis, quote benchmarking, "
        "and deterministic financial lifecycle advisory."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Engine Singletons
diagnosis_engine = ApplianceDiagnosisEngine()
vision_client = ApplianceVisionClient()


# ============================================================================
# HELPER: FALLBACK DIAGNOSTIC RETRIEVER
# ============================================================================

def fallback_retriever_match(
    appliance_type: str,
    brand: str,
    symptom_text: str,
    error_code: Optional[str],
    db: Session,
) -> Tuple[List[RankedCause], str, List[str]]:
    """
    Local domain fallback matcher used when remote model endpoint is unreachable.
    Matches symptom keywords against known part price bands and manual rules.
    """
    logger.info("Executing local fallback retriever for %s %s...", brand, appliance_type)
    text_lower = f"{symptom_text} {error_code or ''}".lower()

    # Query all parts for this appliance category
    bands = (
        db.query(PartPriceBand)
        .filter(PartPriceBand.appliance_category.ilike(f"%{appliance_type}%"))
        .all()
    )

    ranked: List[RankedCause] = []
    safety_alerts: List[str] = []
    triage_level = "ASSISTED_DIY"

    # Emergency keyword checks
    if any(k in text_lower for k in ["shock", "current", "mcb trip", "burning", "smoke", "fire", "spark"]):
        safety_alerts.append(
            "CRITICAL: Life safety or fire hazard detected. Disconnect mains AC power immediately at the MCB."
        )
        triage_level = "EMERGENCY"

    # Map matched components
    rank_idx = 1
    for band in bands:
        part_name = band.part_category.lower()
        score = 0.0

        if "drain" in text_lower and "drain" in part_name:
            score = 0.94
        elif "door" in text_lower and ("door" in part_name or "latch" in part_name):
            score = 0.95
        elif ("inlet" in text_lower or "water tap" in text_lower or "tap" in text_lower) and "inlet" in part_name:
            score = 0.92
        elif ("cooling" in text_lower or "leak" in text_lower or "ec" in text_lower) and "refrigerant" in part_name:
            score = 0.96
        elif ("fan" in text_lower or "blower" in text_lower or "e4" in text_lower) and "fan" in part_name:
            score = 0.91
        elif ("mcb" in text_lower or "element" in text_lower or "hot" in text_lower) and "heating" in part_name:
            score = 0.98
        elif ("compressor" in text_lower or "tik" in text_lower or "click" in text_lower) and "relay" in part_name:
            score = 0.93
        elif ("uv" in text_lower or "beep" in text_lower) and "uv" in part_name:
            score = 0.97
        elif ("pcb" in text_lower or "board" in text_lower) and "pcb" in part_name:
            score = 0.85

        if score > 0.0:
            difficulty = (
                "Technician Required"
                if "compressor" in part_name or "refrigerant" in part_name or "pcb" in part_name
                else "Moderate DIY" if "drain" in part_name or "door" in part_name or "element" in part_name
                else "Easy DIY"
            )

            ranked.append(
                RankedCause(
                    rank=rank_idx,
                    cause=f"Defective or choked {band.part_category}",
                    technical_description=(
                        f"Root cause consistent with {brand} {appliance_type} reported symptom. "
                        f"Requires verifying {band.part_category} electrical resistance and physical clearance."
                    ),
                    part_category=band.part_category,
                    diy_difficulty=difficulty,
                    cost_band={"low": band.low_price_threshold, "high": band.high_price_threshold},
                    estimated_labor_hours=band.typical_labor_hours,
                    probability_score=score,
                )
            )
            rank_idx += 1

    # Fallback default if no specific keyword matched
    if not ranked:
        default_band = bands[0] if bands else None
        low = default_band.low_price_threshold if default_band else 800.0
        high = default_band.high_price_threshold if default_band else 2500.0
        cat = default_band.part_category if default_band else "Internal Sensor or Control Module"
        ranked.append(
            RankedCause(
                rank=1,
                cause=f"Component wear or mechanical obstruction in {cat}",
                technical_description="Internal component breakdown detected based on appliance operating symptom.",
                part_category=cat,
                diy_difficulty="Moderate DIY",
                cost_band={"low": low, "high": high},
                estimated_labor_hours=1.2,
                probability_score=0.75,
            )
        )

    # Sort ranked causes by probability score descending
    ranked.sort(key=lambda x: x.probability_score, reverse=True)
    for i, r in enumerate(ranked):
        r.rank = i + 1

    return ranked, triage_level, safety_alerts


# ============================================================================
# API ENDPOINT 1: POST /api/diagnose
# ============================================================================

@app.post("/api/diagnose", response_model=DiagnoseResponse, status_code=status.HTTP_200_OK)
def diagnose_appliance(
    req: DiagnoseRequest,
    db: Session = Depends(get_db),
):
    """
    Accepts appliance type, brand, age, and symptom text.
    Queries the fine-tuned Adaption model endpoint (with a local fallback retriever
    matching rows if the host is unavailable) to return ranked causes with low/high
    cost bands and DIY difficulty.
    """
    logger.info("Received /api/diagnose request for %s %s (Age: %.1f yrs)", req.brand, req.appliance_type, req.age)

    # 1. Fetch Appliance Reference Benchmark for Lifespan & Running Cost
    ref = (
        db.query(ApplianceReference)
        .filter(ApplianceReference.appliance_type.ilike(f"%{req.appliance_type}%"))
        .first()
    )

    baseline_life = ref.baseline_lifespan if ref else 10.0
    age_ratio = req.age / baseline_life if baseline_life > 0 else 0.5

    if age_ratio < 0.35:
        age_assessment = f"Early Lifecycle: At {req.age:.1f} years, this appliance is within its initial prime lifespan ({baseline_life:.0f} yr baseline). Repair is strongly favored."
    elif age_ratio <= 0.75:
        age_assessment = f"Mid Lifecycle: At {req.age:.1f} years, the appliance has used {age_ratio:.0%} of its expected {baseline_life:.0f} yr lifespan. Compare repair quote against replacement."
    else:
        age_assessment = f"Late Lifecycle: At {req.age:.1f} years, this unit is near or beyond its expected {baseline_life:.0f} yr baseline. Major repairs carry high risk of cascading breakdowns."

    # 2. Try Remote Adaption Diagnosis Engine, Fallback to Retriever
    source_used = "adaption_model"
    ranked_causes: List[RankedCause] = []
    safety_alerts: List[str] = []
    triage_level = "ASSISTED_DIY"

    try:
        diag_req = DiagnosticRequest(
            appliance_type=req.appliance_type,
            symptom_description=req.symptom_text,
            brand=req.brand,
            model_number=req.model,
            error_code=req.error_code,
        )
        diag_resp: DiagnosticResponse = diagnosis_engine.diagnose(diag_req)
        safety_alerts = diag_resp.safety_precautions
        triage_level = diag_resp.triage_level

        # Map diagnosis engine text causes to part price bands
        for idx, cause_text in enumerate(diag_resp.probable_causes[:4]):
            # Cross-reference with DB Part Price Bands
            matched_band = (
                db.query(PartPriceBand)
                .filter(
                    PartPriceBand.appliance_category.ilike(f"%{req.appliance_type}%"),
                )
                .all()
            )
            # Find best keyword match in part categories
            chosen_band = None
            for b in matched_band:
                if any(word in cause_text.lower() for word in b.part_category.lower().split()):
                    chosen_band = b
                    break
            if not chosen_band and matched_band:
                chosen_band = matched_band[idx % len(matched_band)]

            low_cost = chosen_band.low_price_threshold if chosen_band else 750.0
            high_cost = chosen_band.high_price_threshold if chosen_band else 2200.0
            labor_hrs = chosen_band.typical_labor_hours if chosen_band else 1.2
            part_cat = chosen_band.part_category if chosen_band else "Diagnostic Component"

            diff = "Easy DIY" if "filter" in cause_text.lower() or "latch" in cause_text.lower() else "Technician Required" if "compressor" in cause_text.lower() or "leak" in cause_text.lower() else "Moderate DIY"

            ranked_causes.append(
                RankedCause(
                    rank=idx + 1,
                    cause=cause_text,
                    technical_description=f"Identified diagnostic root cause for {req.brand} {req.appliance_type}.",
                    part_category=part_cat,
                    diy_difficulty=diff,
                    cost_band={"low": low_cost, "high": high_cost},
                    estimated_labor_hours=labor_hrs,
                    probability_score=round(max(0.5, 0.95 - (idx * 0.12)), 2),
                )
            )

    except Exception as err:
        logger.warning("Adaption model endpoint unavailable (%s). Engaging fallback retriever.", err)
        source_used = "fallback_retriever"
        ranked_causes, triage_level, safety_alerts = fallback_retriever_match(
            req.appliance_type, req.brand, req.symptom_text, req.error_code, db
        )

    # 3. Create or Update Persistent Case Record
    case_id = req.case_id or f"case_{uuid.uuid4().hex[:12]}"
    case_record = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()

    user_snapshot = {
        "appliance_type": req.appliance_type,
        "brand": req.brand,
        "age": req.age,
        "symptom_text": req.symptom_text,
        "model": req.model,
        "error_code": req.error_code,
    }

    diagnosis_payload = {
        "age_assessment": age_assessment,
        "triage_level": triage_level,
        "safety_alerts": safety_alerts,
        "ranked_causes": [
            (r.model_dump() if hasattr(r, "model_dump") else r.dict())
            for r in ranked_causes
        ],
        "source": source_used,
    }

    if not case_record:
        case_record = CaseRecord(
            id=case_id,
            user_input_snapshot=user_snapshot,
            returned_diagnosis=diagnosis_payload,
        )
        db.add(case_record)
    else:
        case_record.user_input_snapshot = user_snapshot
        case_record.returned_diagnosis = diagnosis_payload
        case_record.updated_at = datetime.datetime.utcnow()

    db.commit()

    return DiagnoseResponse(
        case_id=case_id,
        appliance_type=req.appliance_type,
        brand=req.brand,
        age_assessment=age_assessment,
        triage_level=triage_level,
        safety_alerts=safety_alerts,
        ranked_causes=ranked_causes,
        reference_benchmark=ref.to_dict() if ref else None,
        source=source_used,
    )


# ============================================================================
# API ENDPOINT 2: POST /api/quote-check
# ============================================================================

@app.post("/api/quote-check", response_model=QuoteCheckResponse, status_code=status.HTTP_200_OK)
def check_repair_quote(
    req: QuoteCheckRequest,
    db: Session = Depends(get_db),
):
    """
    Compares a user-submitted repair quote against part_price_bands to flag
    whether parts and labor rates look reasonable, inflated, or predatory.
    """
    logger.info(
        "Checking repair quote for %s -> %s (Quoted Part: %.2f, Labor: %s)",
        req.appliance_category,
        req.part_category,
        req.quoted_part_price,
        req.quoted_labor_price,
    )

    # 1. Query Reference Price Band from Database
    band = (
        db.query(PartPriceBand)
        .filter(
            PartPriceBand.appliance_category.ilike(f"%{req.appliance_category}%"),
            PartPriceBand.part_category.ilike(f"%{req.part_category}%"),
        )
        .first()
    )

    # Fuzzy match on part category if exact match fails
    if not band:
        band = (
            db.query(PartPriceBand)
            .filter(PartPriceBand.appliance_category.ilike(f"%{req.appliance_category}%"))
            .first()
        )

    if not band:
        raise HTTPException(
            status_code=404,
            detail=f"No price benchmark bands found for category '{req.appliance_category}' and part '{req.part_category}'.",
        )

    low_p = band.low_price_threshold
    high_p = band.high_price_threshold
    median_p = (low_p + high_p) / 2.0
    typical_labor = band.typical_labor_hours * band.typical_labor_rate_hourly

    # 2. Evaluate Part Price Status & Variance
    part_variance = ((req.quoted_part_price - high_p) / high_p) * 100.0 if req.quoted_part_price > high_p else (
        ((req.quoted_part_price - low_p) / low_p) * 100.0 if req.quoted_part_price < low_p else 0.0
    )

    advisory_notes: List[str] = []

    if req.quoted_part_price > high_p:
        part_status = "inflated"
        advisory_notes.append(
            f"⚠️ Part price of ₹{req.quoted_part_price:,.2f} is {part_variance:+.1f}% ABOVE the benchmark high threshold of ₹{high_p:,.2f}."
        )
    elif req.quoted_part_price < (low_p * 0.65):
        part_status = "unusually_low"
        advisory_notes.append(
            f"⚠️ Part price of ₹{req.quoted_part_price:,.2f} is unusually low. Verify if the technician is quoting a refurbished or duplicate non-OEM part."
        )
    else:
        part_status = "fair"
        advisory_notes.append(
            f"✅ Part price of ₹{req.quoted_part_price:,.2f} falls within the standard OEM fair price band (₹{low_p:,.2f} – ₹{high_p:,.2f})."
        )

    # 3. Evaluate Labor Price Status
    labor_variance: Optional[float] = None
    labor_status = "unknown"

    if req.quoted_labor_price is not None:
        labor_variance = ((req.quoted_labor_price - typical_labor) / typical_labor) * 100.0 if typical_labor > 0 else 0.0
        if req.quoted_labor_price > (typical_labor * 1.35):
            labor_status = "inflated"
            advisory_notes.append(
                f"⚠️ Quoted labor of ₹{req.quoted_labor_price:,.2f} exceeds standard labor benchmark of ₹{typical_labor:,.2f} by {labor_variance:+.1f}%."
            )
        elif req.quoted_labor_price < (typical_labor * 0.50):
            labor_status = "unusually_low"
            advisory_notes.append(f"ℹ️ Labor rate of ₹{req.quoted_labor_price:,.2f} is lower than typical market rate (₹{typical_labor:,.2f}).")
        else:
            labor_status = "fair"
            advisory_notes.append(f"✅ Quoted labor of ₹{req.quoted_labor_price:,.2f} is fair and competitive (Benchmark: ₹{typical_labor:,.2f}).")

    # 4. Overall Assessment
    if part_status == "inflated" or labor_status == "inflated":
        overall_status = "inflated"
    elif part_status == "unusually_low":
        overall_status = "warning"
    else:
        overall_status = "reasonable"

    benchmarks = {
        "part_low_threshold": low_p,
        "part_high_threshold": high_p,
        "part_median": median_p,
        "typical_labor_hours": band.typical_labor_hours,
        "typical_labor_rate_hourly": band.typical_labor_rate_hourly,
        "typical_labor_total": typical_labor,
        "expected_total_range": {
            "low": round(low_p + typical_labor, 2),
            "high": round(high_p + typical_labor, 2),
        },
    }

    variance_data = {
        "part_variance_percentage": round(part_variance, 2),
        "labor_variance_percentage": round(labor_variance, 2) if labor_variance is not None else None,
    }

    return QuoteCheckResponse(
        appliance_category=band.appliance_category,
        part_category=band.part_category,
        part_status=part_status,
        labor_status=labor_status,
        overall_status=overall_status,
        benchmarks=benchmarks,
        variance=variance_data,
        advisory_notes=advisory_notes,
    )


# ============================================================================
# API ENDPOINT 3: POST /api/verdict
# ============================================================================

@app.post("/api/verdict", response_model=VerdictResponse, status_code=status.HTTP_200_OK)
def calculate_verdict(
    req: VerdictRequest,
    db: Session = Depends(get_db),
):
    """
    Passes structured cost fields into the deterministic cost_engine module
    and returns comparative breakdown, verdict, sensitivity status, and flip assumption.
    """
    logger.info("Executing /api/verdict: Q=%.2f, P=%.2f, L_r=%.1f, L_n=%.1f", req.Q, req.P, req.L_r, req.L_n)

    cost_inputs = {
        "Q": req.Q,
        "tr": req.tr,
        "tn": req.tn,
        "v": req.v,
        "p": req.p,
        "E_old": req.E_old,
        "E_new": req.E_new,
        "L_r": req.L_r,
        "L_n": req.L_n,
        "P": req.P,
        "D": req.D,
        "S": req.S,
    }

    try:
        # Run deterministic calculations in cost_engine
        cost_results = calculate_annualized_costs(cost_inputs, sensitivity_pct=req.sensitivity_pct)
        flip_sentence = find_flip_point(cost_inputs)
        flip_details = calculate_flip_points(cost_inputs)
    except Exception as calc_err:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Cost engine calculation error: {str(calc_err)}")

    # Update database record if case_id provided
    if req.case_id:
        case_record = db.query(CaseRecord).filter(CaseRecord.id == req.case_id).first()
        if case_record:
            case_record.cost_parameters = cost_inputs
            case_record.final_verdict = {
                "verdict": cost_results["verdict"],
                "confidence": cost_results["confidence"],
                "annual_repair_cost": cost_results["annual_repair_cost"],
                "annual_replace_cost": cost_results["annual_replace_cost"],
                "annual_savings": cost_results["annual_savings"],
                "flip_assumption": flip_sentence,
                "volatile_parameters": cost_results["volatile_parameters"],
            }
            case_record.updated_at = datetime.datetime.utcnow()
            db.commit()

    return VerdictResponse(
        case_id=req.case_id,
        verdict=cost_results["verdict"],
        confidence=cost_results["confidence"],
        volatile_parameters=cost_results["volatile_parameters"],
        volatile_parameter=cost_results["volatile_parameter"],
        annual_repair_cost=cost_results["annual_repair_cost"],
        annual_replace_cost=cost_results["annual_replace_cost"],
        annual_savings=cost_results["annual_savings"],
        total_repair_cost=cost_results["total_repair_cost"],
        total_replace_cost=cost_results["total_replace_cost"],
        annual_difference=cost_results["annual_difference"],
        is_tie=cost_results["is_tie"],
        flip_assumption=flip_sentence,
        tipping_points=flip_details.get("tipping_points", {}),
        breakdown=cost_results["breakdown"],
        recommendation_summary=cost_results["recommendation_summary"],
    )


# ============================================================================
# API ENDPOINT 4: POST /api/photo
# ============================================================================

@app.post("/api/photo", response_model=PhotoExtractionResponse, status_code=status.HTTP_200_OK)
async def upload_model_photo(
    file: UploadFile = File(..., description="Appliance model rating plate / sticker image"),
    hint_brand: Optional[str] = Form(None),
    hint_type: Optional[str] = Form(None),
):
    """
    Receives an uploaded model sticker image/file, routes it to the vision client,
    and extracts brand, model, serial number, and technical specifications.
    """
    logger.info("Received image upload for model sticker extraction: %s (%s)", file.filename, file.content_type)

    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"Uploaded file '{file.filename}' is not an image (content-type: {file.content_type}).",
        )

    try:
        contents = await file.read()
        extraction = vision_client.extract_from_image(
            image_bytes=contents,
            filename=file.filename or "sticker.jpg",
            hint_brand=hint_brand,
            hint_type=hint_type,
        )

        return PhotoExtractionResponse(
            brand=extraction["brand"],
            model_number=extraction["model_number"],
            serial_number=extraction.get("serial_number"),
            appliance_type=extraction.get("appliance_type"),
            electrical_specs=extraction.get("electrical_specs", {}),
            detected_error_codes=extraction.get("detected_error_codes", []),
            confidence_score=extraction.get("confidence_score", 0.90),
            raw_extracted_text=extraction.get("raw_extracted_text", ""),
            advisory_tip=extraction.get("advisory_tip", "Rating plate details extracted successfully."),
        )
    except Exception as err:
        logger.error("Failed to extract model info from image: %s", err)
        raise HTTPException(status_code=500, detail=f"Vision model extraction error: {str(err)}")


# ============================================================================
# API ENDPOINT 5: GET /api/cases/{id}
# ============================================================================

@app.get("/api/cases/{case_id}", response_model=CaseResponse, status_code=status.HTTP_200_OK)
def get_case_by_id(
    case_id: str,
    db: Session = Depends(get_db),
):
    """
    Retrieves a saved assessment record by unique identifier.
    Returns input snapshot, AI diagnosis, cost parameters, and final verdict.
    """
    logger.info("Retrieving case record '%s'...", case_id)

    case_record = db.query(CaseRecord).filter(CaseRecord.id == case_id).first()
    if not case_record:
        raise HTTPException(
            status_code=404,
            detail=f"Case assessment with ID '{case_id}' was not found.",
        )

    return CaseResponse(
        id=case_record.id,
        created_at=case_record.created_at.isoformat() if case_record.created_at else "",
        updated_at=case_record.updated_at.isoformat() if case_record.updated_at else "",
        user_input_snapshot=case_record.user_input_snapshot or {},
        returned_diagnosis=case_record.returned_diagnosis,
        cost_parameters=case_record.cost_parameters,
        final_verdict=case_record.final_verdict,
    )


# ============================================================================
# ADDITIONAL REFERENCE & UTILITY ENDPOINTS
# ============================================================================

@app.get("/api/reference/appliances", status_code=status.HTTP_200_OK)
def list_appliance_references(db: Session = Depends(get_db)):
    """Returns baseline lifespans and typical operating costs for all appliances."""
    records = db.query(ApplianceReference).all()
    return [r.to_dict() for r in records]


@app.get("/api/reference/price-bands", status_code=status.HTTP_200_OK)
def list_part_price_bands(
    category: Optional[str] = Query(None, description="Optional filter by appliance category"),
    db: Session = Depends(get_db),
):
    """Returns benchmark price thresholds for repair parts and labor hours."""
    query = db.query(PartPriceBand)
    if category:
        query = query.filter(PartPriceBand.appliance_category.ilike(f"%{category}%"))
    return [p.to_dict() for p in query.all()]


@app.get("/health", status_code=status.HTTP_200_OK)
def health_probe(db: Session = Depends(get_db)):
    """Health check validating database connectivity."""
    db.execute(text("SELECT 1"))
    return {
        "status": "healthy",
        "service": "Repair or Replace Advisor API",
        "database": "connected",
        "timestamp": datetime.datetime.utcnow().isoformat(),
    }


# Static Directory Mount & Single-Page Application (SPA) Root
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
candidate_dirs = [current_dir, parent_dir]

frontend_dist_dir = None
frontend_assets_dir = None
static_dir = None

for d in candidate_dirs:
    f_dist = os.path.join(d, "frontend", "dist")
    if os.path.isdir(f_dist) and not frontend_dist_dir:
        frontend_dist_dir = f_dist
        f_assets = os.path.join(f_dist, "assets")
        if os.path.isdir(f_assets):
            frontend_assets_dir = f_assets
    s_dir = os.path.join(d, "static")
    if os.path.isdir(s_dir) and not static_dir:
        static_dir = s_dir

if frontend_assets_dir:
    app.mount("/assets", StaticFiles(directory=frontend_assets_dir), name="frontend_assets")

if static_dir:
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
def serve_ui():
    """Serves the interactive React Single-Page Application."""
    if frontend_dist_dir:
        dist_index = os.path.join(frontend_dist_dir, "index.html")
        if os.path.exists(dist_index):
            return FileResponse(dist_index)
    if static_dir:
        static_index = os.path.join(static_dir, "index.html")
        if os.path.exists(static_index):
            return FileResponse(static_index)
    return {
        "message": "Repair or Replace Advisor API is active. Open /docs for Swagger documentation.",
        "docs_url": "/docs",
    }


# ============================================================================
# SERVER RUNNER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    app_target = "backend.main:app" if os.path.exists("backend") else "main:app"
    uvicorn.run(app_target, host="0.0.0.0", port=8000, reload=True)

