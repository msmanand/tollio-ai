import { FormEvent, ReactNode, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_TOLLIO_API_URL ?? "http://localhost:8000";

type UrgencyMode = "saver" | "balanced" | "urgent";
type BudgetPeriod = "daily" | "weekly" | "monthly" | "yearly";

type DemoForm = {
  origin: string;
  destination: string;
  arrival_time: string;
  urgency_mode: UrgencyMode;
  budget_period: BudgetPeriod;
  budget_amount: number;
  commute_days_per_week: number;
  trips_per_commute_day: number;
  include_weekends: boolean;
};

type BudgetSummary = {
  spend_to_date: number;
  budget_remaining: number;
  projected_period_spend: number;
  projected_overage: number;
  savings_to_date: number;
  dashboard_message: string;
};

type GantryDecision = {
  gantry_name_or_segment: string;
  action: string;
  toll_cost_avoided: number;
  added_minutes: number;
  budget_effect: string;
  value_score: number;
  reason: string;
};

type RouteSegment = {
  segment_label: string;
  road_name: string;
  start_location: string;
  end_location: string;
  segment_type: string;
  estimated_minutes: number;
  estimated_cost: number;
  distance_miles: number;
};

type MapMarker = {
  marker_type: string;
  label: string;
  latitude: number;
  longitude: number;
  description: string;
};

type CommutePlanResponse = {
  recommended_route_summary: string;
  natural_route_cost: number;
  optimized_route_cost: number;
  estimated_savings: number;
  added_minutes: number;
  budget_impact: string;
  gantry_decisions: GantryDecision[];
  route_segments: RouteSegment[];
  map_markers: MapMarker[];
  explanation: string;
  budget_summary?: BudgetSummary;
};

const friscoPreset: DemoForm = {
  origin: "Frisco",
  destination: "Downtown Dallas",
  arrival_time: "08:30",
  urgency_mode: "balanced",
  budget_period: "daily",
  budget_amount: 8,
  commute_days_per_week: 5,
  trips_per_commute_day: 2,
  include_weekends: false,
};

function commuteBudgets(form: DemoForm) {
  return {
    daily_budget: form.budget_period === "daily" ? form.budget_amount : 8,
    weekly_budget: form.budget_period === "weekly" ? form.budget_amount : 40,
    monthly_budget:
      form.budget_period === "monthly"
        ? form.budget_amount
        : form.budget_period === "yearly"
          ? Math.round((form.budget_amount / 12) * 100) / 100
          : 160,
  };
}

function currency(value: number | undefined) {
  return `$${(value ?? 0).toFixed(2)}`;
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (letter: string) => letter.toUpperCase());
}

export function App() {
  const [form, setForm] = useState<DemoForm>(friscoPreset);
  const [plan, setPlan] = useState<CommutePlanResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const budgetStatus = useMemo(() => {
    if (!plan?.budget_summary) {
      return "Waiting for commute plan";
    }
    if (plan.budget_summary.projected_overage > 0) {
      return "Projected Over";
    }
    if (plan.optimized_route_cost > form.budget_amount) {
      return "At Risk";
    }
    return "On Track";
  }, [form.budget_amount, plan]);

  function updateField<K extends keyof DemoForm>(key: K, value: DemoForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function planCommute(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/commute/plan`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          ...commuteBudgets(form),
          toll_pass_type: "NTTA TollTag",
          vehicle_mpg: 28,
          gas_price: 3.25,
          avoid_excessive_signals: true,
        }),
      });

      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }

      setPlan((await response.json()) as CommutePlanResponse);
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Unknown request failure";
      setError(
        `${message}. Start the API with: cd services/api && source .venv/bin/activate && uvicorn main:app --reload`,
      );
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <main className="app-shell">
      <section className="topbar">
        <div>
          <p className="eyebrow">Tollio AI local demo</p>
          <h1>Budget-aware toll routing dashboard</h1>
        </div>
        <button className="preset-button" type="button" onClick={() => setForm(friscoPreset)}>
          Frisco to Downtown Dallas under $8
        </button>
      </section>

      <section className="workspace">
        <form className="planner-panel" onSubmit={planCommute}>
          <div className="form-grid">
            <label>
              Origin
              <input
                value={form.origin}
                onChange={(event) => updateField("origin", event.target.value)}
              />
            </label>
            <label>
              Destination
              <input
                value={form.destination}
                onChange={(event) => updateField("destination", event.target.value)}
              />
            </label>
            <label>
              Arrival Time
              <input
                value={form.arrival_time}
                onChange={(event) => updateField("arrival_time", event.target.value)}
              />
            </label>
            <label>
              Urgency
              <select
                value={form.urgency_mode}
                onChange={(event) => updateField("urgency_mode", event.target.value as UrgencyMode)}
              >
                <option value="saver">Saver</option>
                <option value="balanced">Balanced</option>
                <option value="urgent">Urgent</option>
              </select>
            </label>
            <label>
              Budget Period
              <select
                value={form.budget_period}
                onChange={(event) => updateField("budget_period", event.target.value as BudgetPeriod)}
              >
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
                <option value="yearly">Yearly</option>
              </select>
            </label>
            <label>
              Budget Amount
              <input
                type="number"
                min="0"
                step="0.01"
                value={form.budget_amount}
                onChange={(event) => updateField("budget_amount", Number(event.target.value))}
              />
            </label>
            <label>
              Commute Days/Week
              <input
                type="number"
                min="1"
                max="7"
                value={form.commute_days_per_week}
                onChange={(event) =>
                  updateField("commute_days_per_week", Number(event.target.value))
                }
              />
            </label>
            <label>
              Trips/Commute Day
              <input
                type="number"
                min="1"
                max="10"
                value={form.trips_per_commute_day}
                onChange={(event) =>
                  updateField("trips_per_commute_day", Number(event.target.value))
                }
              />
            </label>
          </div>

          <label className="checkbox-row">
            <input
              type="checkbox"
              checked={form.include_weekends}
              onChange={(event) => updateField("include_weekends", event.target.checked)}
            />
            Include weekends
          </label>

          <button className="primary-button" type="submit" disabled={isLoading}>
            {isLoading ? "Planning..." : "Plan Commute"}
          </button>
          {error ? <p className="error-text">{error}</p> : null}
        </form>

        <section className="results-panel">
          {plan ? (
            <>
              <div className="summary">
                <p className="eyebrow">Recommendation</p>
                <h2>{plan.recommended_route_summary}</h2>
              </div>

              <div className="metric-grid">
                <Metric label="Natural Cost" value={currency(plan.natural_route_cost)} />
                <Metric label="Optimized Cost" value={currency(plan.optimized_route_cost)} />
                <Metric label="Estimated Savings" value={currency(plan.estimated_savings)} />
                <Metric label="Added Minutes" value={`${plan.added_minutes}`} />
                <Metric label="Budget Status" value={budgetStatus} />
                <Metric
                  label="Budget Remaining"
                  value={currency(plan.budget_summary?.budget_remaining)}
                />
              </div>

              <div className="message-strip">{plan.budget_summary?.dashboard_message}</div>

              <ResultSection title="Gantry Decisions">
                {plan.gantry_decisions.map((decision) => (
                  <article className="list-card" key={`${decision.gantry_name_or_segment}-${decision.action}`}>
                    <div>
                      <strong>{decision.gantry_name_or_segment}</strong>
                      <span>{titleCase(decision.action)}</span>
                    </div>
                    <p>{decision.reason}</p>
                    <small>
                      Avoided {currency(decision.toll_cost_avoided)} · {decision.added_minutes} min ·
                      value {decision.value_score.toFixed(2)}
                    </small>
                  </article>
                ))}
              </ResultSection>

              <ResultSection title="Route Segments">
                {plan.route_segments.map((segment) => (
                  <article className="list-card" key={`${segment.segment_label}-${segment.road_name}`}>
                    <div>
                      <strong>{segment.segment_label}</strong>
                      <span>{titleCase(segment.segment_type)}</span>
                    </div>
                    <p>
                      {segment.road_name}: {segment.start_location} to {segment.end_location}
                    </p>
                    <small>
                      {segment.estimated_minutes} min · {segment.distance_miles} mi ·{" "}
                      {currency(segment.estimated_cost)}
                    </small>
                  </article>
                ))}
              </ResultSection>

              <ResultSection title="Map Markers">
                {plan.map_markers.map((marker) => (
                  <article className="list-card" key={`${marker.marker_type}-${marker.label}`}>
                    <div>
                      <strong>{marker.label}</strong>
                      <span>{titleCase(marker.marker_type)}</span>
                    </div>
                    <p>{marker.description}</p>
                    <small>
                      {marker.latitude.toFixed(4)}, {marker.longitude.toFixed(4)}
                    </small>
                  </article>
                ))}
              </ResultSection>

              <ResultSection title="Explanation">
                <p className="explanation">{plan.explanation}</p>
              </ResultSection>
            </>
          ) : (
            <div className="empty-state">
              <p className="eyebrow">Ready</p>
              <h2>Start the local API, then plan the preset commute.</h2>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function ResultSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="result-section">
      <h3>{title}</h3>
      <div className="result-list">{children}</div>
    </section>
  );
}
