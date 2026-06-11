import json
import os
from typing import Dict
from urllib import request as urllib_request


def gemini_explanation_tool(context: Dict[str, object]) -> Dict[str, object]:
    if not _live_gemini_enabled():
        return {
            "tool_name": "gemini_explanation_tool",
            "status": "mock",
            "gemini_invoked": False,
            "explanation": (
                "Mock Gemini explanation: Tollio recommends the option that saves meaningful toll cost "
                "without adding excessive time."
            ),
            "data_source": "mock_gemini_explanation_tool",
        }

    prompt = (
        "Explain this Tollio commute optimization result in driver-friendly language. "
        "Explain only the provided deterministic Tollio result. Do not invent tolls, routes, or prices. "
        "Do not change toll decisions. Do not invent route data. Use only this JSON:\n"
        f"{json.dumps(context, indent=2)}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.2},
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
    return {
        "tool_name": "gemini_explanation_tool",
        "status": "live",
        "gemini_invoked": True,
        "explanation": text,
        "data_source": "live_gemini",
    }


def _live_gemini_enabled() -> bool:
    return (
        os.getenv("TOLLIO_AGENT_MODE", "mock").strip().lower() == "live"
        and bool(os.getenv("GEMINI_API_KEY", "").strip())
    )
