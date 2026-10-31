"""Rule-based NL query extraction with optional LLM assist."""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any


CITY_ALIASES = {
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "noida": "Noida",
    "greater noida": "Greater Noida",
    "ghaziabad": "Ghaziabad",
    "faridabad": "Faridabad",
    "delhi": "Delhi",
    "dwarka": "Delhi",
    "rohini": "Delhi",
    "indirapuram": "Ghaziabad",
    "vaishali": "Ghaziabad",
}


def _parse_budget(text: str) -> Decimal | None:
    t = text.lower().replace(",", "")
    # ₹80 lakh / 80 lac / 80L
    m = re.search(r"(?:₹\s*)?(\d+(?:\.\d+)?)\s*(lakh|lac|lacs|l)\b", t)
    if m:
        return Decimal(m.group(1)) * Decimal("100000")
    m = re.search(r"(?:₹\s*)?(\d+(?:\.\d+)?)\s*(crore|cr)\b", t)
    if m:
        return Decimal(m.group(1)) * Decimal("10000000")
    m = re.search(r"under\s+(?:₹\s*)?(\d{6,})", t)
    if m:
        return Decimal(m.group(1))
    return None


def extract_search_spec(query: str) -> dict[str, Any]:
    q = query.strip()
    lower = q.lower()
    spec: dict[str, Any] = {
        "purpose": None,
        "min_price": None,
        "max_price": None,
        "bedrooms": None,
        "configuration": None,
        "geographic_areas": [],
        "locality": None,
        "amenity_preferences": [],
        "property_type": None,
    }

    if any(w in lower for w in ["rent", "rental", "lease", "tenant"]):
        spec["purpose"] = "rent"
    elif any(w in lower for w in ["buy", "sale", "purchase", "invest"]):
        spec["purpose"] = "buy"
    else:
        spec["purpose"] = "buy"  # default for NCR discovery MVP

    bhk = re.search(r"(\d)\s*(?:bhk|bedroom)", lower)
    if bhk:
        beds = int(bhk.group(1))
        spec["bedrooms"] = beds
        spec["configuration"] = f"{beds}BHK"

    budget = _parse_budget(lower)
    if budget is not None:
        if "under" in lower or "below" in lower or "upto" in lower or "up to" in lower or "max" in lower:
            spec["max_price"] = str(budget)
        elif "above" in lower or "over" in lower or "min" in lower:
            spec["min_price"] = str(budget)
        else:
            spec["max_price"] = str(budget)

    for alias, city in CITY_ALIASES.items():
        if alias in lower and city not in spec["geographic_areas"]:
            spec["geographic_areas"].append(city)

    for amenity, key in [
        ("metro", "metro"),
        ("hospital", "hospital"),
        ("school", "school"),
        ("park", "park"),
        ("mall", "shopping"),
        ("grocery", "grocery"),
    ]:
        if amenity in lower:
            spec["amenity_preferences"].append(key)

    if "apartment" in lower or "flat" in lower:
        spec["property_type"] = "apartment"
    elif "villa" in lower:
        spec["property_type"] = "villa"
    elif "plot" in lower:
        spec["property_type"] = "plot"

    clarification_required = False
    questions: list[str] = []
    if not spec["geographic_areas"]:
        clarification_required = True
        questions.append("Which city or locality in Delhi NCR should I search?")
    if spec["bedrooms"] is None:
        questions.append("How many bedrooms (BHK) do you prefer?")

    return {
        "search_specification": spec,
        "clarification_required": clarification_required,
        "clarification_questions": questions,
    }
