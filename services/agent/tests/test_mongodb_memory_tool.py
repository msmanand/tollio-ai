from app.tools.mongodb_memory_tool import (
    get_budget_profile_tool,
    get_recent_commutes_tool,
    save_trip_decision_tool,
    update_savings_summary_tool,
)


def test_mongodb_memory_tools_return_structured_output_without_credentials(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    saved = save_trip_decision_tool("sample-plan", "Morning commute", estimated_savings=4.5)
    budget = get_budget_profile_tool()
    recent = get_recent_commutes_tool()
    savings = update_savings_summary_tool(additional_savings=2.0)

    assert saved["saved_trip_id"] == "mock-trip-sample-plan"
    assert saved["data_source"] == "mock_mongodb_memory_tool"
    assert budget["daily_budget"] == 8.0
    assert recent["recent_commutes"]
    assert savings["estimated_total_savings"] == 6.5


def test_mongodb_memory_tool_does_not_require_live_mongodb(monkeypatch):
    monkeypatch.setenv("TOLLIO_STORAGE_MODE", "mock")
    monkeypatch.delenv("MONGODB_URI", raising=False)

    assert get_budget_profile_tool()["data_source"] == "mock_mongodb_memory_tool"
