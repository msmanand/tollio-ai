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

type SegmentType = "toll" | "service_road" | "local_road";

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

function minutesByType(plan: CommutePlanResponse, type: SegmentType) {
  return plan.route_segments
    .filter((segment) => segment.segment_type === type)
    .reduce((total, segment) => total + segment.estimated_minutes, 0);
}

function segmentCostByType(plan: CommutePlanResponse, type: SegmentType) {
  return plan.route_segments
    .filter((segment) => segment.segment_type === type)
    .reduce((total, segment) => total + segment.estimated_cost, 0);
}

function skippedGantryText(plan: CommutePlanResponse) {
  const exitMarker = plan.map_markers.find((marker) => marker.marker_type === "exit");
  const decision = plan.gantry_decisions.find(
    (item) => item.action !== "stay_on_toll" || item.toll_cost_avoided > 0,
  );

  if (exitMarker) {
    return exitMarker.label;
  }
  if (decision) {
    return decision.gantry_name_or_segment;
  }
  return "No gantry skipped";
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

  const routeStats = useMemo(() => {
    if (!plan) {
      return null;
    }

    return {
      tollMinutes: minutesByType(plan, "toll"),
      serviceRoadMinutes: minutesByType(plan, "service_road"),
      localRoadMinutes: minutesByType(plan, "local_road"),
      tollCost: segmentCostByType(plan, "toll"),
      serviceRoadCost: segmentCostByType(plan, "service_road"),
      localRoadCost: segmentCostByType(plan, "local_road"),
    };
  }, [plan]);

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
                <Metric label="Toll-Road Minutes" value={`${routeStats?.tollMinutes ?? 0}`} />
                <Metric
                  label="Service-Road Minutes"
                  value={`${routeStats?.serviceRoadMinutes ?? 0}`}
                />
                <Metric label="Local-Road Minutes" value={`${routeStats?.localRoadMinutes ?? 0}`} />
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

              <RouteIntelligenceMap plan={plan} />

              <section className="why-panel">
                <div>
                  <p className="eyebrow">Why this saves money</p>
                  <h3>{skippedGantryText(plan)}</h3>
                  <p>
                    The optimized route spends {currency(plan.optimized_route_cost)} instead of{" "}
                    {currency(plan.natural_route_cost)}, saving {currency(plan.estimated_savings)}
                    while adding {plan.added_minutes} minutes. Toll-road time is{" "}
                    {routeStats?.tollMinutes ?? 0} minutes, service-road time is{" "}
                    {routeStats?.serviceRoadMinutes ?? 0} minutes, and local-road time is{" "}
                    {routeStats?.localRoadMinutes ?? 0} minutes.
                  </p>
                </div>
                <div className="why-metrics">
                  <span>{budgetStatus}</span>
                  <strong>{currency(plan.budget_summary?.budget_remaining)} left</strong>
                  <small>{plan.budget_impact}</small>
                </div>
              </section>

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

function RouteIntelligenceMap({ plan }: { plan: CommutePlanResponse }) {
  const totalMinutes = Math.max(
    plan.route_segments.reduce((total, segment) => total + segment.estimated_minutes, 0),
    1,
  );
  let cursor = 70;
  const routeWidth = 780;
  const markerCount = Math.max(plan.map_markers.length - 1, 1);

  return (
    <section className="map-panel" aria-label="Mock route intelligence map">
      <div className="map-header">
        <div>
          <p className="eyebrow">Route intelligence map</p>
          <h3>Mock map view from backend route segments</h3>
        </div>
        <div className="legend">
          <span className="legend-item toll">Toll</span>
          <span className="legend-item service_road">Service road</span>
          <span className="legend-item local_road">Local road</span>
        </div>
      </div>

      <svg className="route-svg" viewBox="0 0 920 300" role="img">
        <rect x="20" y="20" width="880" height="260" rx="16" className="map-base" />
        <path d="M45 70 C180 35 300 62 430 45 S690 30 850 70" className="surface-road" />
        <path d="M50 230 C210 205 330 250 500 218 S720 205 875 238" className="surface-road" />

        {plan.route_segments.map((segment, index) => {
          const segmentWidth = Math.max((segment.estimated_minutes / totalMinutes) * routeWidth, 76);
          const x1 = cursor;
          const x2 = Math.min(cursor + segmentWidth, 850);
          cursor = x2;
          const y = segment.segment_type === "service_road" ? 190 : segment.segment_type === "local_road" ? 155 : 125;
          const className = `route-line ${segment.segment_type}`;

          return (
            <g key={`${segment.segment_label}-${segment.road_name}`}>
              <line x1={x1} y1={y} x2={x2} y2={y} className={className} />
              <circle cx={x1} cy={y} r="5" className={`node ${segment.segment_type}`} />
              <circle cx={x2} cy={y} r="5" className={`node ${segment.segment_type}`} />
              <text x={(x1 + x2) / 2} y={y - 20} textAnchor="middle" className="segment-label">
                {segment.segment_label}
              </text>
              <text x={(x1 + x2) / 2} y={y + 34} textAnchor="middle" className="segment-meta">
                {segment.estimated_minutes} min · {currency(segment.estimated_cost)}
              </text>
              {index < plan.route_segments.length - 1 ? (
                <line
                  x1={x2}
                  y1={y}
                  x2={x2 + 18}
                  y2={plan.route_segments[index + 1].segment_type === "service_road" ? 190 : 125}
                  className="connector-line"
                />
              ) : null}
            </g>
          );
        })}

        {plan.map_markers.map((marker, index) => {
          const x = 70 + (index / markerCount) * routeWidth;
          const y = marker.marker_type === "exit" || marker.marker_type === "reentry" ? 190 : 125;

          return (
            <g key={`${marker.marker_type}-${marker.label}`}>
              <line x1={x} y1={y - 42} x2={x} y2={y - 12} className="marker-stem" />
              <circle cx={x} cy={y - 50} r="13" className={`marker-dot ${marker.marker_type}`} />
              <text x={x} y={y - 46} textAnchor="middle" className="marker-letter">
                {marker.marker_type.slice(0, 1).toUpperCase()}
              </text>
              <text x={x} y={y - 68} textAnchor="middle" className="marker-label">
                {marker.label}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="segment-strip">
        {plan.route_segments.map((segment) => (
          <div className={`segment-chip ${segment.segment_type}`} key={`${segment.segment_label}-chip`}>
            <strong>{segment.road_name}</strong>
            <span>
              {titleCase(segment.segment_type)} · {segment.estimated_minutes} min ·{" "}
              {currency(segment.estimated_cost)}
            </span>
          </div>
        ))}
      </div>
    </section>
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
