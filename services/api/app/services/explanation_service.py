import json
import os
from typing import Any, List, Optional
from urllib import request as urllib_request

from pydantic import BaseModel


class ExplanationBundle(BaseModel):
    short_explanation: str
    detailed_explanation: str
    driver_friendly_summary: str
    caution_notes: List[str]
    data_source: str
    live_error: Optional[str] = None


def generate_explanation(commute_plan_output: Any) -> ExplanationBundle:
    if _live_gemini_enabled():
        try:
            return _generate_live_gemini_explanation(commute_plan_output)
        except Exception as exc:
            return _generate_mock_explanation(
                commute_plan_output,
                data_source="mock_gemini_fallback",
                live_error=exc.__class__.__name__,
            )
    return _generate_mock_explanation(commute_plan_output)


def _generate_mock_explanation(
    commute_plan_output: Any,
    data_source: str = "mock_explanation_service",
    live_error: Optional[str] = None,
) -> ExplanationBundle:
    decisions = list(getattr(commute_plan_output, "gantry_decisions", []))
    total_toll_avoided = round(sum(decision.toll_cost_avoided for decision in decisions), 2)
    total_added_minutes = sum(decision.added_minutes for decision in decisions)
    first_decision = decisions[0] if decisions else None
    first_decision_text = (
        f"{first_decision.gantry_name_or_segment}: {first_decision.action.value}"
        if first_decision
        else "No gantry decision available"
    )

    short = (
        f"Tollio keeps the optimized route at ${commute_plan_output.optimized_route_cost:.2f}, "
        f"saving about ${commute_plan_output.estimated_savings:.2f} versus the natural toll route."
    )
    detailed = (
        f"Budget impact: {commute_plan_output.budget_impact} "
        f"The deterministic gantry engine found {len(decisions)} gantry decision(s), "
        f"including {first_decision_text}. Across the decisions, the plan identifies "
        f"${total_toll_avoided:.2f} in toll avoided with {total_added_minutes} added minutes. "
        "Gemini is not allowed to change toll decisions or invent route data."
    )
    summary = (
        "Take the gantry-aware route: pay for the toll segments that are worth it, "
        "skip low-value scanners, and stay within the selected toll budget."
    )
    notes = [
        "Decisions come from Tollio's deterministic Gantry Intelligence Engine.",
        "Live Gemini explanations are disabled unless TOLLIO_AGENT_MODE=live and GEMINI_API_KEY is set.",
    ]
    if live_error:
        notes.append(f"Live Gemini path was attempted but returned {live_error}.")
    return ExplanationBundle(
        short_explanation=short,
        detailed_explanation=detailed,
        driver_friendly_summary=summary,
        caution_notes=notes,
        data_source=data_source,
        live_error=live_error,
    )


def _live_gemini_enabled() -> bool:
    return (
        os.getenv("TOLLIO_AGENT_MODE", "mock").strip().lower() == "live"
        and bool(os.getenv("GEMINI_API_KEY", "").strip())
    )


def _generate_live_gemini_explanation(commute_plan_output: Any) -> ExplanationBundle:
    prompt = _build_gemini_prompt(commute_plan_output)
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt,
                    }
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }
    api_key = os.environ["GEMINI_API_KEY"]
    req = urllib_request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib_request.urlopen(req, timeout=10) as response:
        response_payload = json.loads(response.read().decode("utf-8"))

    text = response_payload["candidates"][0]["content"]["parts"][0]["text"]
    parsed = json.loads(text)
    return ExplanationBundle(
        short_explanation=parsed["short_explanation"],
        detailed_explanation=parsed["detailed_explanation"],
        driver_friendly_summary=parsed["driver_friendly_summary"],
        caution_notes=parsed.get("caution_notes", []),
        data_source="live_gemini",
    )


def _build_gemini_prompt(commute_plan_output: Any) -> str:
    return (
        "You are explaining Tollio AI commute output to a driver.\n"
        "Do not change toll decisions.\n"
        "Do not invent route data.\n"
        "Explain only the provided deterministic Tollio result. Do not invent tolls, routes, or prices.\n"
        "Explain only the provided deterministic route/gantry/budget output.\n"
        "Return JSON with short_explanation, detailed_explanation, "
        "driver_friendly_summary, and caution_notes.\n\n"
        f"Commute output:\n{json.dumps(commute_plan_output.model_dump(mode='json'), indent=2)}"
    )
