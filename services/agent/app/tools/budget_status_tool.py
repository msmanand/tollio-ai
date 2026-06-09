from app.models import AgentRequest, BudgetPeriod, BudgetStatus


def budget_status_tool(request: AgentRequest, projected_toll_spend: float) -> BudgetStatus:
    """Evaluate whether the selected budget period is preserved."""
    limit = _budget_limit(request)
    remaining = round(limit - projected_toll_spend, 2)
    is_preserved = remaining >= 0
    status = "budget_preserved" if is_preserved else "budget_exceeded"
    return BudgetStatus(
        budget_period=request.budget_period,
        budget_limit=limit,
        projected_toll_spend=projected_toll_spend,
        remaining_budget=remaining,
        is_budget_preserved=is_preserved,
        status=status,
    )


def _budget_limit(request: AgentRequest) -> float:
    if request.budget_period == BudgetPeriod.daily:
        return request.daily_budget
    if request.budget_period == BudgetPeriod.weekly:
        return request.weekly_budget
    return request.monthly_budget
