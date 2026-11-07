"""
models.py
=========
SQLAlchemy Database Models for the Repair or Replace Advisor.

Models:
1. ApplianceReference : Baseline appliance lifespans, operating costs, and failure lists.
2. PartPriceBand     : Fair price thresholds (low/high) and benchmark labor hours for parts.
3. CaseRecord        : Historical snapshot of user inputs, diagnosis, financial inputs, and verdicts.
"""

from __future__ import annotations

import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    JSON,
    String,
    Text,
)
try:
    from backend.database import Base
except ImportError:
    from database import Base


class ApplianceReference(Base):
    """
    Reference table for appliance baseline parameters.
    Used for comparative age benchmarking and default operating cost estimates.
    """
    __tablename__ = "appliance_reference"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appliance_type = Column(String(100), unique=True, index=True, nullable=False)
    baseline_lifespan = Column(Float, nullable=False, default=10.0)  # years
    typical_yearly_running_cost = Column(Float, nullable=False, default=2500.0)  # currency/yr
    common_failure_list = Column(JSON, nullable=False, default=list)  # list of common failure descriptions
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "appliance_type": self.appliance_type,
            "baseline_lifespan": self.baseline_lifespan,
            "typical_yearly_running_cost": self.typical_yearly_running_cost,
            "common_failure_list": self.common_failure_list,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PartPriceBand(Base):
    """
    Industry benchmark price bands for repair parts and typical labor durations.
    Used by /api/quote-check to flag price inflation or predatory contractor estimates.
    """
    __tablename__ = "part_price_bands"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    appliance_category = Column(String(100), index=True, nullable=False)
    part_category = Column(String(100), index=True, nullable=False)
    low_price_threshold = Column(Float, nullable=False)  # lowest fair OEM/aftermarket price
    high_price_threshold = Column(Float, nullable=False) # highest fair OEM dealer price
    typical_labor_hours = Column(Float, nullable=False, default=1.5)  # typical hours
    typical_labor_rate_hourly = Column(Float, nullable=False, default=400.0)  # hourly labor rate
    notes = Column(Text, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "appliance_category": self.appliance_category,
            "part_category": self.part_category,
            "low_price_threshold": self.low_price_threshold,
            "high_price_threshold": self.high_price_threshold,
            "typical_labor_hours": self.typical_labor_hours,
            "typical_labor_rate_hourly": self.typical_labor_rate_hourly,
            "notes": self.notes,
        }


class CaseRecord(Base):
    """
    Persistent assessment session.
    Stores the full lifecycle: user inputs -> AI diagnosis -> cost engine inputs -> final verdict.
    Enables reopening and auditing via a unique identifier.
    """
    __tablename__ = "cases"

    id = Column(String(64), primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, nullable=False)
    
    # JSON Snapshots preserving historical context
    user_input_snapshot = Column(JSON, nullable=False, default=dict)
    returned_diagnosis = Column(JSON, nullable=True)
    cost_parameters = Column(JSON, nullable=True)
    final_verdict = Column(JSON, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "user_input_snapshot": self.user_input_snapshot,
            "returned_diagnosis": self.returned_diagnosis,
            "cost_parameters": self.cost_parameters,
            "final_verdict": self.final_verdict,
        }

