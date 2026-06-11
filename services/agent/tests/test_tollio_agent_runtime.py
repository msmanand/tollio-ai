import json
import subprocess
import sys

from app.tollio_agent_runtime import run_agent_runtime
from app.tools.gemini_explanation_tool import gemini_explanation_tool


def test_runtime_orchestrates_required_tools(monkeypatch):
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    output = run_agent_runtime()

    assert output["entry_point"] == "python -m app.tollio_agent_runtime"
    assert output["route_toll_optimization"]["route_options_tool_called"] is True
    assert output["route_toll_optimization"]["toll_estimate_tool_called"] is True
    assert output["route_toll_optimization"]["gantry_intelligence_tool_called"] is True
    assert output["budget"]["status"]
    assert output["gemini_explanation"]["gemini_invoked"] is False
    assert {item["tool_name"] for item in output["memory_trace"]} == {
        "save_trip_decision_tool",
        "get_recent_commutes_tool",
        "update_savings_summary_tool",
    }
    assert all(item["mcp_config_present"] is True for item in output["memory_trace"])


def test_runtime_module_command_prints_structured_output(monkeypatch):
    monkeypatch.setenv("TOLLIO_AGENT_MODE", "mock")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    completed = subprocess.run(
        [sys.executable, "-m", "app.tollio_agent_runtime"],
        check=True,
        capture_output=True,
        text=True,
    )
    body = json.loads(completed.stdout)

    assert body["runtime"] == "Agent Builder / ADK-compatible Tollio runtime"
    assert body["memory_trace"]
    assert body["gemini_explanation"]["data_source"] == "mock_gemini_explanation_tool"


def test_agent_gemini_tool_invokes_live_path_when_gated(monkeypatch):
    calls = []

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def read(self):
            return b'{"candidates":[{"content":{"parts":[{"text":"live runtime explanation"}]}}]}'

    def fake_urlopen(req, timeout):
        calls.append((req.full_url, timeout))
        return FakeResponse()

    monkeypatch.setenv("TOLLIO_AGENT_MODE", "live")
    monkeypatch.setenv("GEMINI_API_KEY", "test-only-key")
    monkeypatch.setattr("app.tools.gemini_explanation_tool.urllib_request.urlopen", fake_urlopen)

    output = gemini_explanation_tool({"sample": "context"})

    assert output["gemini_invoked"] is True
    assert output["data_source"] == "live_gemini"
    assert output["explanation"] == "live runtime explanation"
    assert calls
