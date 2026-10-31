"""Conversational AI orchestration with grounded tool use."""

from __future__ import annotations

import json
import re
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from app.ai.query_parser import extract_search_spec
from app.ai.tools import (
    calculate_investment_scenario_tool,
    compare_properties_tool,
    get_nearby_amenities_tool,
    get_price_benchmarks_tool,
    get_property_details_tool,
    search_properties_tool,
)
from app.core.config import get_settings
from app.schemas.ai import AIChatRequest, AIChatResponse, AISearchRequest, AISearchResponse

settings = get_settings()


def run_ai_search(db: Session, req: AISearchRequest) -> AISearchResponse:
    parsed = extract_search_spec(req.query)
    spec = parsed["search_specification"]
    if parsed["clarification_required"] and not spec.get("geographic_areas"):
        return AISearchResponse(
            search_specification=spec,
            clarification_required=True,
            clarification_questions=parsed["clarification_questions"],
            results_reference=None,
            results=[],
            explanation="I need a clearer location before searching. I will not invent listings.",
            limitations=["Essential geographic constraint is ambiguous."],
        )

    tool_out = search_properties_tool(
        db,
        {
            **spec,
            "city": (spec.get("geographic_areas") or [None])[0],
            "page_size": 10,
        },
    )
    ref = uuid4()
    return AISearchResponse(
        search_specification=spec,
        clarification_required=False,
        clarification_questions=parsed["clarification_questions"],
        results_reference=ref,
        results=tool_out["results"],
        explanation="Filters extracted from your request and applied as hard constraints before ranking.",
        limitations=[
            "Results are limited to published, authorised inventory in the EstateAI database.",
            "Amenity preferences are shown for review; they do not invent missing facilities.",
        ],
    )


def _classify_intent(message: str, property_ids: list[UUID]) -> str:
    m = message.lower()
    if property_ids and ("compare" in m or "vs" in m or "versus" in m):
        return "comparison"
    if any(w in m for w in ["yield", "investment", "roi", "rental income"]):
        return "investment"
    if any(w in m for w in ["near", "neighbourhood", "neighborhood", "amenity", "metro", "hospital"]):
        return "locality"
    if property_ids or any(w in m for w in ["tell me about", "details", "this property"]):
        return "property_qa"
    if any(w in m for w in ["find", "search", "show me", "looking for", "2bhk", "3bhk"]):
        return "discovery"
    return "property_qa" if property_ids else "discovery"


def _maybe_llm_explain(prompt: str) -> str | None:
    if not settings.google_api_key:
        return None
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        resp = model.generate_content(
            prompt
            + "\n\nRules: Use only the provided evidence. Never invent property IDs, prices, or amenities. "
            "Label estimates clearly. If data is missing, say so."
        )
        return (resp.text or "").strip()
    except Exception:
        return None


def run_ai_chat(db: Session, req: AIChatRequest) -> AIChatResponse:
    intent = _classify_intent(req.message, req.property_ids)
    citations: list[dict[str, Any]] = []
    property_refs: list[str] = []
    assumptions: list[str] = []
    limitations: list[str] = [
        "AI orchestrates retrieval; listings and calculations come from backend tools.",
        "Not legal, tax, or investment advice.",
    ]
    evidence: dict[str, Any] = {"intent": intent}

    if intent == "discovery":
        search = run_ai_search(db, AISearchRequest(query=req.message))
        evidence["search"] = search.model_dump(mode="json")
        citations.append({"type": "search_specification", "value": search.search_specification})
        property_refs = [str(r.get("id")) for r in search.results]
        answer = (
            f"Extracted filters: {json.dumps(search.search_specification)}. "
            f"Found {len(search.results)} matching published listings."
        )
        if search.results:
            titles = ", ".join(f"{r.get('title')} ({r.get('locality')})" for r in search.results[:5])
            answer += f" Top matches: {titles}."
        else:
            answer += " No inventory matched hard constraints — try relaxing budget or locality."
        llm = _maybe_llm_explain(
            f"User asked: {req.message}\nEvidence JSON:\n{json.dumps(evidence)[:6000]}\nWrite a concise grounded answer."
        )
        if llm:
            answer = llm

    elif intent == "comparison":
        ids = [str(p) for p in req.property_ids[:4]]
        if len(ids) < 2:
            return AIChatResponse(
                answer="Please provide at least two property IDs to compare (up to four).",
                limitations=limitations,
                follow_up_suggestions=["Select 2–4 properties from search results and ask again."],
            )
        cmp = compare_properties_tool(db, ids)
        evidence["comparison"] = cmp
        citations.append({"type": "compare_properties", "count": len(cmp["properties"])})
        property_refs = [str(p["id"]) for p in cmp["properties"]]
        lines = []
        for p in cmp["properties"]:
            price = p.get("asking_price") or p.get("monthly_rent")
            lines.append(
                f"- {p.get('title')}: {p.get('configuration')}, {p.get('locality')}, "
                f"price/rent={price}, area={p.get('area')}"
            )
        answer = "Comparison (consistent definitions applied):\n" + "\n".join(lines)
        if cmp["missing_ids"]:
            limitations.append(f"Missing/unavailable IDs: {cmp['missing_ids']}")
        llm = _maybe_llm_explain(
            f"Compare these properties for the user request '{req.message}'. Evidence:\n{json.dumps(cmp)[:6000]}"
        )
        if llm:
            answer = llm

    elif intent == "locality":
        if not req.property_ids:
            return AIChatResponse(
                answer="Share a property ID to fetch nearby amenities.",
                follow_up_suggestions=["Open a property and ask about metro/hospitals nearby."],
                limitations=limitations,
            )
        pid = str(req.property_ids[0])
        neigh = get_nearby_amenities_tool(db, pid)
        evidence["neighbourhood"] = neigh
        citations.append({"type": "amenities", "property_id": pid, "count": len(neigh.get("amenities", []))})
        property_refs = [pid]
        top = neigh.get("amenities", [])[:5]
        summary = ", ".join(f"{a['name']} ({a['category']}, ~{int(a['distance']['value'])}m)" for a in top)
        answer = f"Nearby amenities (estimated road distance): {summary or 'none in radius'}."
        limitations.extend(neigh.get("limitations") or [])

    elif intent == "investment":
        if not req.property_ids:
            return AIChatResponse(
                answer="Provide a property ID (or explicit purchase_price and monthly_rent) for yield calculation.",
                limitations=limitations,
            )
        detail = get_property_details_tool(db, str(req.property_ids[0]))
        if detail.get("error"):
            return AIChatResponse(answer=detail["error"], limitations=limitations)
        purchase = DecimalLike(detail.get("asking_price"))
        rent = DecimalLike(detail.get("monthly_rent"))
        if purchase is None:
            # try parse from message
            m = re.search(r"price\s*[:=]?\s*(\d+(?:\.\d+)?)", req.message.lower().replace(",", ""))
            purchase = DecimalLike(m.group(1)) if m else None
        if rent is None:
            m = re.search(r"rent\s*[:=]?\s*(\d+(?:\.\d+)?)", req.message.lower().replace(",", ""))
            rent = DecimalLike(m.group(1)) if m else None
        if purchase is None or rent is None:
            return AIChatResponse(
                answer="Need both purchase price and expected monthly rent for a deterministic yield calculation.",
                assumptions=assumptions,
                limitations=limitations + ["Missing price or rent inputs."],
                property_references=[str(req.property_ids[0])],
            )
        inv = calculate_investment_scenario_tool(
            {"purchase_price": purchase, "monthly_rent": rent, "property_id": str(req.property_ids[0])}
        )
        evidence["investment"] = inv
        citations.append({"type": "calculate_investment_scenario", "version": inv.get("calculation_version")})
        property_refs = [str(req.property_ids[0])]
        assumptions = inv.get("assumptions") or []
        limitations.extend(inv.get("limitations") or [])
        answer = (
            f"Gross yield {inv['gross_yield_pct']}% | Net yield {inv['net_yield_pct']}% "
            f"on acquisition cost {inv['total_acquisition_cost']}. {inv['disclaimer']}"
        )

    else:  # property_qa
        if not req.property_ids:
            search = run_ai_search(db, AISearchRequest(query=req.message))
            return AIChatResponse(
                answer=search.explanation
                + (f" Found {len(search.results)} listings." if search.results else " No matches."),
                citations=[{"type": "search", "spec": search.search_specification}],
                property_references=[str(r.get("id")) for r in search.results],
                limitations=search.limitations,
                follow_up_suggestions=["Ask about a specific property ID for sourced details."],
            )
        pid = str(req.property_ids[0])
        detail = get_property_details_tool(db, pid)
        price = get_price_benchmarks_tool(db, pid)
        evidence["detail"] = detail
        evidence["price"] = price
        citations.append({"type": "listing", "property_id": pid})
        citations.append({"type": "price_analysis", "listing_id": price.get("listing_id")})
        property_refs = [pid]
        limitations.extend(detail.get("limitations") or [])
        limitations.extend(price.get("limitations") or [])
        answer = (
            f"{detail.get('title')} in {detail.get('locality')}: {detail.get('configuration')}, "
            f"purpose={detail.get('purpose')}, asking={detail.get('asking_price')}, "
            f"rent={detail.get('monthly_rent')}, area={detail.get('area')}. "
            f"Price/sqft={price.get('asking_price_per_sq_ft')} ({price.get('area_basis')})."
        )
        llm = _maybe_llm_explain(
            f"Answer the user question using only this evidence.\nQuestion: {req.message}\n{json.dumps(evidence)[:6000]}"
        )
        if llm:
            answer = llm

    return AIChatResponse(
        answer=answer,
        citations=citations,
        property_references=property_refs,
        assumptions=assumptions,
        limitations=limitations,
        follow_up_suggestions=[
            "Compare up to four shortlisted properties",
            "Ask about nearby metro and hospitals",
            "Run a rental yield scenario",
        ],
        usage_metadata={"intent": intent, "llm_used": bool(settings.google_api_key)},
    )


def DecimalLike(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
