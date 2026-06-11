import { FormEvent, ReactNode, useEffect, useMemo, useState } from "react";

const API_BASE_URL = import.meta.env.VITE_TOLLIO_API_URL ?? "http://localhost:8000";

type RoadOption = {
  road_id: number;
  road_short: string;
  road_name: string;
  exit_count: number;
  source_file: string;
  effective_date: string;
  confidence: string;
};

type ExitOption = {
  exit_index: number;
  exit_name: string;
};

type OptimizeForm = {
  road: string;
  from_exit: string;
  to_exit: string;
  payment: "tolltag" | "zipcash";
  mpg: number;
  gas_price: number;
  vehicle_type: "gas" | "hybrid" | "ev";
  traffic_mode: "rush" | "offpeak" | "night";
};

type BrainOption = {
  entry: string;
  exit: string;
  toll_price: number;
  natural_price: number;
  toll_saved: number;
  service_road_minutes: number;
  service_road_miles: number;
  gas_cost: number;
  net_saving: number;
  entry_value_score: number;
  exit_value_score: number;
  combined_value_score: number;
  wasted_behind: number;
  unused_ahead: number;
  recommendation_label: string;
  plain_english_reason: string;
};

type Recommendation = {
  natural_entry: string;
  better_entry: string;
  natural_exit: string;
  better_exit: string;
  toll_saved: number;
  gas_cost: number;
  net_saving: number;
  extra_time_minutes: number;
  natural_value_score: number;
  optimized_value_score: number;
  annual_saving_projection: number;
  plain_english_reason: string;
};

type OptimizeResponse = {
  natural_route: BrainOption;
  optimized_route: BrainOption;
  ranked_options: BrainOption[];
  explanation: string;
  recommendation: Recommendation;
  source_metadata: {
    source_file: string;
    effective_date: string;
    payment_types: string[];
    confidence: string;
  };
};

const defaultForm: OptimizeForm = {
  road: "DNT",
  from_exit: "Walnut Hill/Royal",
  to_exit: "Trinity Mills/Frankford",
  payment: "tolltag",
  mpg: 28,
  gas_price: 3.25,
  vehicle_type: "gas",
  traffic_mode: "offpeak",
};

function currency(value: number | undefined | null) {
  return `$${(value ?? 0).toFixed(2)}`;
}

export function App() {
  const [form, setForm] = useState<OptimizeForm>(defaultForm);
  const [roads, setRoads] = useState<RoadOption[]>([]);
  const [exits, setExits] = useState<ExitOption[]>([]);
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/ntta/roads`)
      .then((response) => (response.ok ? response.json() : { roads: [] }))
      .then((body: { roads: RoadOption[] }) => {
        setRoads(body.roads);
        const first = body.roads[0];
        if (first && !body.roads.some((road) => road.road_short === form.road)) {
          setForm((current) => ({ ...current, road: first.road_short }));
        }
      })
      .catch(() => setRoads([]));
  }, []);

  useEffect(() => {
    if (!form.road) {
      return;
    }
    fetch(`${API_BASE_URL}/api/v1/ntta/exits?road=${encodeURIComponent(form.road)}`)
      .then((response) => (response.ok ? response.json() : { exits: [] }))
      .then((body: { exits: ExitOption[] }) => {
        setExits(body.exits);
        if (!body.exits.length) {
          return;
        }
        setForm((current) => {
          const fromExists = body.exits.some((exit) => exit.exit_name === current.from_exit);
          const toExists = body.exits.some((exit) => exit.exit_name === current.to_exit);
          return {
            ...current,
            from_exit: fromExists ? current.from_exit : body.exits[0].exit_name,
            to_exit: toExists ? current.to_exit : body.exits[Math.min(11, body.exits.length - 1)].exit_name,
          };
        });
      })
      .catch(() => setExits([]));
  }, [form.road]);

  const selectedRoad = useMemo(
    () => roads.find((road) => road.road_short === form.road || road.road_name === form.road),
    [form.road, roads],
  );

  function update<K extends keyof OptimizeForm>(key: K, value: OptimizeForm[K]) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function optimize(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/optimize/entry-exit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!response.ok) {
        throw new Error(`API returned ${response.status}`);
      }
      setResult((await response.json()) as OptimizeResponse);
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
          <h1>NTTA toll utilization optimizer</h1>
        </div>
        <button className="preset-button" type="button" onClick={() => setForm(defaultForm)}>
          DNT Royal to Trinity Mills
        </button>
      </section>

      <section className="workspace">
        <form className="planner-panel" onSubmit={optimize}>
          <div className="form-grid">
            <label>
              Road
              <select value={form.road} onChange={(event) => update("road", event.target.value)}>
                {roads.map((road) => (
                  <option key={road.road_short} value={road.road_short}>
                    {road.road_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              From / Begin Trip
              <select value={form.from_exit} onChange={(event) => update("from_exit", event.target.value)}>
                {exits.map((exit) => (
                  <option key={`from-${exit.exit_index}`} value={exit.exit_name}>
                    {exit.exit_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              To / End Trip
              <select value={form.to_exit} onChange={(event) => update("to_exit", event.target.value)}>
                {exits.map((exit) => (
                  <option key={`to-${exit.exit_index}`} value={exit.exit_name}>
                    {exit.exit_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Payment Type
              <select value={form.payment} onChange={(event) => update("payment", event.target.value as OptimizeForm["payment"])}>
                <option value="tolltag">TollTag</option>
                <option value="zipcash">ZipCash</option>
              </select>
            </label>
            <label>
              Traffic
              <select value={form.traffic_mode} onChange={(event) => update("traffic_mode", event.target.value as OptimizeForm["traffic_mode"])}>
                <option value="rush">Rush</option>
                <option value="offpeak">Offpeak</option>
                <option value="night">Night</option>
              </select>
            </label>
            <label>
              Vehicle
              <select value={form.vehicle_type} onChange={(event) => update("vehicle_type", event.target.value as OptimizeForm["vehicle_type"])}>
                <option value="gas">Gas</option>
                <option value="hybrid">Hybrid</option>
                <option value="ev">EV</option>
              </select>
            </label>
            <label>
              MPG
              <input type="number" min="0" step="0.1" value={form.mpg} onChange={(event) => update("mpg", Number(event.target.value))} />
            </label>
            <label>
              Gas Price
              <input type="number" min="0" step="0.01" value={form.gas_price} onChange={(event) => update("gas_price", Number(event.target.value))} />
            </label>
          </div>

          <button className="primary-button" type="submit" disabled={isLoading || !exits.length}>
            {isLoading ? "Optimizing..." : "Optimize Entry / Exit"}
          </button>
          {error ? <p className="error-text">{error}</p> : null}
          {selectedRoad ? (
            <p className="source-note">
              Matrix source: {selectedRoad.source_file} · {selectedRoad.effective_date} · {selectedRoad.confidence}
            </p>
          ) : null}
        </form>

        <section className="results-panel">
          {result ? (
            <>
              <section className="summary">
                <p className="eyebrow">Recommended</p>
                <h2>
                  Enter at {result.recommendation.better_entry} instead of {result.recommendation.natural_entry}
                </h2>
                <p>
                  Exit at {result.recommendation.better_exit} instead of {result.recommendation.natural_exit}.
                  Save {currency(result.recommendation.net_saving)} net, add{" "}
                  {result.recommendation.extra_time_minutes} minutes on service roads, and improve value score
                  from {result.recommendation.natural_value_score}% to{" "}
                  {result.recommendation.optimized_value_score}%.
                </p>
              </section>

              <div className="metric-grid">
                <Metric label="Natural Toll" value={currency(result.natural_route.toll_price)} />
                <Metric label="Optimized Toll" value={currency(result.optimized_route.toll_price)} />
                <Metric label="Toll Saved" value={currency(result.optimized_route.toll_saved)} />
                <Metric label="Gas Cost" value={currency(result.optimized_route.gas_cost)} />
                <Metric label="Net Saved" value={currency(result.optimized_route.net_saving)} />
                <Metric label="Extra Time" value={`${result.optimized_route.service_road_minutes} min`} />
                <Metric label="Entry Score" value={`${result.optimized_route.entry_value_score}%`} />
                <Metric label="Exit Score" value={`${result.optimized_route.exit_value_score}%`} />
                <Metric label="Combined Score" value={`${result.optimized_route.combined_value_score}%`} />
              </div>

              <section className="why-panel">
                <div>
                  <p className="eyebrow">Why</p>
                  <h3>{result.optimized_route.recommendation_label}</h3>
                  <p>{result.explanation}</p>
                </div>
                <div className="why-metrics">
                  <span>Annual projection</span>
                  <strong>{currency(result.recommendation.annual_saving_projection)}</strong>
                  <small>{result.source_metadata.source_file}</small>
                </div>
              </section>

              <section className="brain-comparison">
                <RouteCard title="Natural Route" option={result.natural_route} />
                <RouteCard title="Optimized Route" option={result.optimized_route} isBest />
              </section>

              <ResultSection title="Ranked Alternatives">
                {result.ranked_options.slice(0, 3).map((option) => (
                  <article className="list-card" key={`${option.recommendation_label}-${option.entry}-${option.exit}`}>
                    <div>
                      <strong>{option.recommendation_label}</strong>
                      <span>{option.combined_value_score}% value</span>
                    </div>
                    <p>
                      {option.entry} to {option.exit}: {option.plain_english_reason}
                    </p>
                    <small>
                      Toll {currency(option.toll_price)} · net {currency(option.net_saving)} · service road{" "}
                      {option.service_road_minutes} min / {option.service_road_miles} mi
                    </small>
                    <small>
                      Wasted behind: {option.wasted_behind} exits · unused ahead: {option.unused_ahead} exits
                    </small>
                  </article>
                ))}
              </ResultSection>
            </>
          ) : (
            <div className="empty-state">
              <p className="eyebrow">Ready</p>
              <h2>Select an NTTA road, begin trip, end trip, and payment type.</h2>
            </div>
          )}
        </section>
      </section>
    </main>
  );
}

function RouteCard({
  title,
  option,
  isBest = false,
}: {
  title: string;
  option: BrainOption;
  isBest?: boolean;
}) {
  return (
    <article className={`brain-card ${isBest ? "best" : ""}`}>
      <div>
        <p className="eyebrow">{isBest ? "Recommended" : "Comparison"}</p>
        <h3>{title}</h3>
      </div>
      <p>
        {option.entry} to {option.exit}
      </p>
      <div className="brain-card-metrics">
        <span>Toll {currency(option.toll_price)}</span>
        <span>Net {currency(option.net_saving)}</span>
        <span>Value {option.combined_value_score}%</span>
        <span>Service road {option.service_road_minutes} min</span>
      </div>
    </article>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
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
