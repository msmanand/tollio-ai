from app.agent import tollio_commute_agent
from app.models import AgentRequest


if __name__ == "__main__":
    request = AgentRequest(
        user_message=(
            "Get me from Frisco to downtown Dallas by 8:30, "
            "but keep me under my $8 daily toll budget."
        ),
        origin="Frisco",
        destination="Downtown Dallas",
        arrival_time="08:30",
        urgency_mode="balanced",
        daily_budget=8.0,
        weekly_budget=40.0,
        monthly_budget=160.0,
        budget_period="daily",
        toll_pass_type="NTTA TollTag",
        vehicle_mpg=28.0,
        gas_price=3.25,
        avoid_excessive_signals=True,
    )
    print(tollio_commute_agent(request).model_dump_json(indent=2))
