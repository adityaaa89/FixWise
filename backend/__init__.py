"""
Repair or Replace Advisor - Backend Package
===========================================
Modular architecture for diagnostic triage, quote benchmarking, and deterministic
financial lifecycle optimization.
"""

from backend.adaption_pipeline import (
    estimate_job_cost,
    run_appliance_pipeline,
)
from backend.cost_engine import (
    calculate_annualized_costs,
    calculate_flip_points,
    find_flip_point,
    run_uncertainty_analysis,
)
from backend.main import app

__all__ = [
    "app",
    "calculate_annualized_costs",
    "calculate_flip_points",
    "estimate_job_cost",
    "find_flip_point",
    "run_appliance_pipeline",
    "run_uncertainty_analysis",
]

