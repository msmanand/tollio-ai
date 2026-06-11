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
  runtime_data_source: "mongodb" | "local_json";
  original_rate_source: string;
  source_confidence: string;
};

type ExitOption = {
  exit_index: number;
  exit_name: string;
};

type OptimizeForm = {
  from_road: string;
  from_exit: string;
  to_road: string;
  to_exit: string;
  payment: "tolltag" | "zipcash";
  mpg: number;
  gas_price: number;
  vehicle_type: "gas" | "hybrid" | "ev";
  traffic_mode: "rush" | "offpeak" | "night";
};

type BrainOption = {
  label: string;
  route_path_label: string;
  entry: string;
  exit: string;
  entry_instruction: string;
  exit_instruction: string;
  toll_cost: number;
  toll_price: number;
  natural_toll_cost: number;
  natural_price: number;
  toll_saved: number;
  net_savings: number;
  service_road_minutes: number;
  added_minutes: number;
  service_road_miles: number;
  gas_cost: number;
  net_saving: number;
  value_score: number;
  entry_value_score: number;
  exit_value_score: number;
  combined_value_score: number;
  wasted_behind: number;
  unused_ahead: number;
  confidence: string;
  why: string;
  explanation: string;
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
  best_recommendation: BrainOption;
  ranked_options: BrainOption[];
  all_candidates: BrainOption[];
  explanation: string;
  recommendation: Recommendation;
  source_metadata: {
    runtime_data_source: "mongodb" | "local_json";
    original_rate_source: string;
    source_file: string;
    effective_date: string;
    payment_types: string[];
    confidence: string;
    source_confidence: string;
  };
};

const defaultForm: OptimizeForm = {
  from_road: "DNT",
  from_exit: "Walnut Hill/Royal",
  to_road: "DNT",
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

function runtimeSourceLabel(source: "mongodb" | "local_json" | string | undefined) {
  return source === "mongodb" ? "MongoDB" : "Local JSON fallback";
}

export function App() {
  const [form, setForm] = useState<OptimizeForm>(defaultForm);
  const [roads, setRoads] = useState<RoadOption[]>([]);
  const [fromExits, setFromExits] = useState<ExitOption[]>([]);
  const [toExits, setToExits] = useState<ExitOption[]>([]);
  const [result, setResult] = useState<OptimizeResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/v1/ntta/roads`)
      .then((response) => (response.ok ? response.json() : { roads: [] }))
      .then((body: { roads: RoadOption[] }) => {
        setRoads(body.roads);
        const first = body.roads[0];
        if (first && !body.roads.some((road) => road.road_short === form.from_road)) {
          setForm((current) => ({ ...current, from_road: first.road_short, to_road: first.road_short }));
        }
      })
      .catch(() => setRoads([]));
  }, []);

  useEffect(() => {
    if (!form.from_road) {
      return;
    }
    fetch(`${API_BASE_URL}/api/v1/ntta/exits?road=${encodeURIComponent(form.from_road)}`)
      .then((response) => (response.ok ? response.json() : { exits: [] }))
      .then((body: { exits: ExitOption[] }) => {
        setFromExits(body.exits);
        if (!body.exits.length) {
          return;
        }
        setForm((current) => {
          const fromExists = body.exits.some((exit) => exit.exit_name === current.from_exit);
          return {
            ...current,
            from_exit: fromExists ? current.from_exit : body.exits[0].exit_name,
            to_exit: current.to_exit,
          };
        });
      })
      .catch(() => setFromExits([]));
  }, [form.from_road]);

  useEffect(() => {
    if (!form.to_road) {
      return;
    }
    fetch(`${API_BASE_URL}/api/v1/ntta/exits?road=${encodeURIComponent(form.to_road)}`)
      .then((response) => (response.ok ? response.json() : { exits: [] }))
      .then((body: { exits: ExitOption[] }) => {
        setToExits(body.exits);
        if (!body.exits.length) {
          return;
        }
        setForm((current) => {
          const toExists = body.exits.some((exit) => exit.exit_name === current.to_exit);
          return {
            ...current,
            to_exit: toExists ? current.to_exit : body.exits[Math.min(11, body.exits.length - 1)].exit_name,
          };
        });
      })
      .catch(() => setToExits([]));
  }, [form.to_road]);

  const selectedRoad = useMemo(
    () => roads.find((road) => road.road_short === form.from_road || road.road_name === form.from_road),
    [form.from_road, roads],
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
              From Road
              <select value={form.from_road} onChange={(event) => update("from_road", event.target.value)}>
                {roads.map((road) => (
                  <option key={road.road_short} value={road.road_short}>
                    {road.road_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              From Exit
              <select value={form.from_exit} onChange={(event) => update("from_exit", event.target.value)}>
                {fromExits.map((exit) => (
                  <option key={`from-${exit.exit_index}`} value={exit.exit_name}>
                    {exit.exit_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              To Road
              <select value={form.to_road} onChange={(event) => update("to_road", event.target.value)}>
                {roads.map((road) => (
                  <option key={`to-road-${road.road_short}`} value={road.road_short}>
                    {road.road_name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              To Exit
              <select value={form.to_exit} onChange={(event) => update("to_exit", event.target.value)}>
                {toExits.map((exit) => (
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

          <button className="primary-button" type="submit" disabled={isLoading || !fromExits.length || !toExits.length}>
            {isLoading ? "Optimizing..." : "Optimize Entry / Exit"}
          </button>
          {error ? <p className="error-text">{error}</p> : null}
          {selectedRoad ? (
            <p className="source-note">
              Data: Runtime source: {runtimeSourceLabel(selectedRoad.runtime_data_source)} · Rate source:{" "}
              {selectedRoad.original_rate_source} · Effective: {selectedRoad.effective_date} · Confidence:{" "}
              {selectedRoad.source_confidence}
            </p>
          ) : null}
        </form>

        <section className="results-panel">
          {result ? (
            <>
              <RecommendationSummary result={result} />

              <div className="metric-grid">
                <Metric label="Natural Toll" value={currency(result.natural_route.toll_price)} />
                <Metric label="Recommended Toll" value={currency(result.best_recommendation.toll_price)} />
                <Metric label="Toll Saved" value={currency(result.best_recommendation.toll_saved)} />
                <Metric label="Gas Cost" value={currency(result.best_recommendation.gas_cost)} />
                <Metric label="Net Saved" value={currency(result.best_recommendation.net_savings)} />
                <Metric label="Extra Time" value={`${result.best_recommendation.added_minutes} min`} />
                <Metric label="Entry Score" value={`${result.best_recommendation.entry_value_score}%`} />
                <Metric label="Exit Score" value={`${result.best_recommendation.exit_value_score}%`} />
                <Metric label="Confidence" value={result.best_recommendation.confidence} />
              </div>

              <section className="why-panel">
                <div>
                  <p className="eyebrow">Why</p>
                  <h3>{result.best_recommendation.label}</h3>
                  <p>{result.explanation}</p>
                </div>
                <div className="why-metrics">
                  <span>Annual projection</span>
                  <strong>{currency(result.recommendation.annual_saving_projection)}</strong>
                  <small>
                    Runtime source: {runtimeSourceLabel(result.source_metadata.runtime_data_source)} · Rate source:{" "}
                    {result.source_metadata.original_rate_source}
                  </small>
                </div>
              </section>

              <section className="brain-comparison">
                {result.all_candidates.map((option) => (
                  <RouteCard
                    title={option.label}
                    option={option}
                    isBest={option.label === result.best_recommendation.label}
                    key={`${option.label}-${option.entry}-${option.exit}`}
                  />
                ))}
              </section>

              <ResultSection title="Ranked Alternatives">
                {result.ranked_options.map((option) => (
                  <article className="list-card" key={`${option.recommendation_label}-${option.entry}-${option.exit}`}>
                    <div>
                      <strong>{option.label}</strong>
                      <span>{option.value_score}% value · {option.confidence}</span>
                    </div>
                    <p>
                      {option.route_path_label}: {option.entry_instruction}; {option.exit_instruction}.
                    </p>
                    <p>{option.explanation}</p>
                    <small>
                      Toll {currency(option.toll_cost)} · saved {currency(option.toll_saved)} · net{" "}
                      {currency(option.net_savings)} · extra time {option.added_minutes} min
                    </small>
                  </article>
                ))}
              </ResultSection>
            </>
          ) : (
            <div className="empty-state">
              <p className="eyebrow">Ready</p>
              <h2>Select from road, from exit, to road, to exit, and payment type.</h2>
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
        {option.route_path_label}: {option.entry_instruction}; {option.exit_instruction}
      </p>
      <div className="brain-card-metrics">
        <span>Toll {currency(option.toll_cost)}</span>
        <span>Saved {currency(option.toll_saved)}</span>
        <span>Net {currency(option.net_savings)}</span>
        <span>Extra time {option.added_minutes} min</span>
        <span>Value {option.value_score}%</span>
        <span>{option.confidence}</span>
      </div>
    </article>
  );
}

function RecommendationSummary({ result }: { result: OptimizeResponse }) {
  const best = result.best_recommendation;
  const entryLine =
    best.entry === result.natural_route.entry
      ? `Enter at ${best.entry}`
      : `Enter at ${best.entry} instead of ${result.natural_route.entry}`;
  const exitLine =
    best.exit === result.natural_route.exit
      ? `Exit at ${best.exit}`
      : `Exit at ${best.exit} instead of ${result.natural_route.exit}`;
  const valueLine =
    best.value_score > result.natural_route.value_score
      ? `Value score improves from ${result.natural_route.value_score}% to ${best.value_score}%.`
      : best.value_score < result.natural_route.value_score
        ? `Value score changes from ${result.natural_route.value_score}% to ${best.value_score}%.`
        : `Value score stays at ${best.value_score}%.`;

  return (
    <section className="summary">
      <p className="eyebrow">Recommended</p>
      <h2>{entryLine}</h2>
      <p>
        {exitLine}. Save {currency(best.net_savings)} net. Extra time: {best.added_minutes} min. {valueLine}
      </p>
      <p>{best.explanation}</p>
    </section>
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
