"""
advisor_tools.py
================
LLM Tool & Function-Calling Interface for the Repair or Replace Advisor.

Enforces the strict system boundary:
"The language model must NEVER do arithmetic or financial calculations;
all math must happen inside the deterministic cost engine."

Provides:
- OpenAI / Gemini / Anthropic compatible function definitions
- Tool calling router & dispatcher
- Automated payload validation and error containment
"""

from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

try:
    from backend.cost_engine import (
        calculate_annualized_costs,
        calculate_flip_points,
        find_flip_point,
        run_uncertainty_analysis,
    )
except ImportError:
    from cost_engine import (
        calculate_annualized_costs,
        calculate_flip_points,
        find_flip_point,
        run_uncertainty_analysis,
    )

# Standardized JSON Schema definition for Function Calling
CALCULATE_ANNUALIZED_COSTS_TOOL_SCHEMA = {
    "name": "calculate_annualized_costs",
    "description": (
        "Deterministically computes total costs, annualized costs (per year), monetary difference, "
        "uncertainty sensitivity confidence ('firm' vs 'close'), and returns the definitive decision "
        "verdict ('Repair' or 'Replace'). The LLM MUST call this tool rather than calculating math itself."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "Q": {"type": "number", "description": "Repair quote / parts and labor cost ($ or ₹)"},
            "tr": {"type": "number", "description": "Time lost / hassle hours dealing with repair (hours)"},
            "tn": {"type": "number", "description": "Time lost / hassle hours buying and installing replacement (hours)"},
            "v": {"type": "number", "description": "Monetary value of consumer's time ($/hour or ₹/hour)"},
            "p": {"type": "number", "description": "Probability of repeat breakdown within extended lifespan (0.0 to 1.0)"},
            "E_old": {"type": "number", "description": "Annual operating / energy cost of old appliance ($/yr or ₹/yr)"},
            "E_new": {"type": "number", "description": "Annual operating / energy cost of new appliance ($/yr or ₹/yr)"},
            "L_r": {"type": "number", "description": "Expected extended lifespan if repaired (years, strictly > 0)"},
            "L_n": {"type": "number", "description": "Expected lifespan of new replacement appliance (years, strictly > 0)"},
            "P": {"type": "number", "description": "Purchase sticker price of new replacement ($ or ₹)"},
            "D": {"type": "number", "description": "Delivery, installation, and haul-away fee ($ or ₹)", "default": 0.0},
            "S": {"type": "number", "description": "Salvage, trade-in, or utility rebate credit received ($ or ₹)", "default": 0.0},
            "sensitivity_pct": {"type": "number", "description": "Uncertainty testing shift (default 0.20 for +/-20%)", "default": 0.20},
        },
        "required": ["Q", "tr", "tn", "v", "p", "E_old", "E_new", "L_r", "L_n", "P"],
    },
}

FIND_FLIP_POINT_TOOL_SCHEMA = {
    "name": "find_flip_point",
    "description": (
        "Calculates the exact tipping point variable change (e.g., how many years L_r needs to last, "
        "or how low the repair quote Q needs to be) required to flip the verdict, returning a clean, "
        "human-readable explanation sentence."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "Q": {"type": "number", "description": "Repair quote ($ or ₹)"},
            "tr": {"type": "number", "description": "Time lost repair (hours)"},
            "tn": {"type": "number", "description": "Time lost replace (hours)"},
            "v": {"type": "number", "description": "Value of time"},
            "p": {"type": "number", "description": "Probability of repeat failure (0.0 to 1.0)"},
            "E_old": {"type": "number", "description": "Old annual operating cost"},
            "E_new": {"type": "number", "description": "New annual operating cost"},
            "L_r": {"type": "number", "description": "Repair lifespan (years)"},
            "L_n": {"type": "number", "description": "New lifespan (years)"},
            "P": {"type": "number", "description": "New purchase price"},
            "D": {"type": "number", "description": "Delivery/install fee", "default": 0.0},
            "S": {"type": "number", "description": "Salvage/rebate credit", "default": 0.0},
        },
        "required": ["Q", "tr", "tn", "v", "p", "E_old", "E_new", "L_r", "L_n", "P"],
    },
}

ADVISOR_TOOLS_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Any]] = {
    "calculate_annualized_costs": calculate_annualized_costs,
    "find_flip_point": find_flip_point,
    "calculate_flip_points": calculate_flip_points,
    "run_uncertainty_analysis": run_uncertainty_analysis,
}


def dispatch_tool_call(tool_name: str, arguments: Union[str, Dict[str, Any]]) -> str:
    """
    Executes tool invocation called by an LLM agent, guaranteeing deterministic computation.
    Returns JSON-stringified output for the LLM response context.
    """
    if isinstance(arguments, str):
        try:
            parsed_args = json.loads(arguments)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"Invalid JSON arguments: {str(e)}"})
    else:
        parsed_args = arguments

    handler = ADVISOR_TOOLS_REGISTRY.get(tool_name)
    if not handler:
        return json.dumps({
            "error": f"Unknown tool '{tool_name}'. Available tools: {list(ADVISOR_TOOLS_REGISTRY.keys())}"
        })

    try:
        result = handler(parsed_args)
        if isinstance(result, str):
            return json.dumps({"result": result})
        return json.dumps(result)
    except Exception as err:
        return json.dumps({"error": f"Tool execution failed: {type(err).__name__} - {str(err)}"})


def get_all_tool_schemas() -> List[Dict[str, Any]]:
    """Returns the full list of tool definitions for LLM initialization."""
    return [
        CALCULATE_ANNUALIZED_COSTS_TOOL_SCHEMA,
        FIND_FLIP_POINT_TOOL_SCHEMA,
    ]

