import { useEffect, useMemo, useState } from "react";
import { getPerformance } from "../api";

function fmt(value, digits = 1) {
  if (value == null || Number.isNaN(Number(value))) return "-";
  return Number(value).toFixed(digits);
}

function raceLabel(race) {
  if (!race) return "-";
  return `${race.year} R${String(race.round).padStart(2, "0")} · ${race.name}`;
}

function yearRange(years) {
  if (!Array.isArray(years) || !years.length) return "-";
  const sorted = [...years].sort((a, b) => a - b);
  return sorted.length === 1 ? String(sorted[0]) : `${sorted[0]}-${sorted[sorted.length - 1]}`;
}

export default function Performance() {
  const [perf, setPerf] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getPerformance()
      .then(data => {
        setPerf(data);
        setError("");
      })
      .catch(() => setError("No performance export found. Run python -m backend.exporters performance."));
  }, []);

  const featureMax = useMemo(() => {
    const features = perf?.random_forest?.feature_importance || [];
    return Math.max(...features.map(feature => feature.importance), 0.01);
  }, [perf]);

  if (error) {
    return (
      <main className="view show">
        <div className="wrap">
          <section className="perf-hero compact">
            <span className="eyebrow">04 · Performance</span>
            <h1>Model Performance</h1>
            <p>{error}</p>
          </section>
        </div>
      </main>
    );
  }

  if (!perf) {
    return (
      <main className="view show">
        <div className="wrap">
          <section className="perf-hero compact">
            <span className="eyebrow">04 · Performance</span>
            <h1>Model Performance</h1>
            <p>Loading the latest model export...</p>
          </section>
        </div>
      </main>
    );
  }

  const cards = perf.random_forest.cards || [];
  const features = perf.random_forest.feature_importance || [];
  const accuracy = perf.monte_carlo.accuracy || {};
  const bands = perf.monte_carlo.bands || [];
  const raceErrors = accuracy.race_errors || [];
  const bestRaces = raceErrors.slice(0, 4);
  const hardestRaces = raceErrors.slice(-4).reverse();
  const trainYears = yearRange(perf.train_seasons);
  const testYears = yearRange(perf.test_seasons) || perf.test_season || "-";

  return (
    <main className="view show">
      <div className="wrap">
        <section className="perf-hero">
          <div>
            <span className="eyebrow">04 · Performance</span>
            <h1>Model Performance</h1>
            <p>
              Random Forest holdout metrics, Monte Carlo backtest accuracy, and
              the feature signals currently doing the most work.
            </p>
          </div>
          <div className="perf-summary-card">
            <span>Train</span>
            <strong>{trainYears}</strong>
            <span>Holdouts</span>
            <strong>{testYears}</strong>
            <span>Historical calls</span>
            <strong>{accuracy.race_count || 0}</strong>
          </div>
        </section>

        <section className="perf-grid">
          {cards.map(card => (
            <article className="perf-card" key={card.key}>
              <span className="perf-card-label">{card.label}</span>
              <strong>{fmt(card.value, card.unit === "%" ? 1 : 2)}<small>{card.unit}</small></strong>
              <p>{card.detail}</p>
            </article>
          ))}
        </section>

        <section className="perf-panels">
          <article className="perf-panel wide">
            <div className="panel-head">
              <span className="eyebrow">Random Forest</span>
              <h2>Feature Importance</h2>
            </div>
            <div className="feature-bars">
              {features.map((feature, index) => (
                <div className="feature-row" key={feature.feature}>
                  <div className="feature-rank">{String(index + 1).padStart(2, "0")}</div>
                  <div className="feature-meta">
                    <div className="feature-name">{feature.label}</div>
                    <div className="feature-group">{feature.group}</div>
                  </div>
                  <div className="feature-track">
                    <i style={{ width: `${(feature.importance / featureMax) * 100}%` }} />
                  </div>
                  <div className="feature-val">{fmt(feature.percent, 2)}%</div>
                </div>
              ))}
            </div>
          </article>

          <article className="perf-panel">
            <div className="panel-head">
              <span className="eyebrow">Monte Carlo</span>
              <h2>Historical Accuracy</h2>
            </div>
            <div className="accuracy-rings">
              {bands.map(band => (
                <div className="accuracy-band" key={band.label}>
                  <span>{band.label}</span>
                  <strong>{fmt(band.value, 1)}<small>{band.unit}</small></strong>
                  <div className="band-track"><i style={{ width: `${band.value || 0}%` }} /></div>
                </div>
              ))}
            </div>
            <div className="perf-mini-stats">
              <div><span>Overall MAE</span><strong>{fmt(accuracy.overall_mae, 2)}<small>pos</small></strong></div>
              <div><span>Top 10 MAE</span><strong>{fmt(accuracy.top_10_mae, 2)}<small>pos</small></strong></div>
              <div><span>Median Err</span><strong>{fmt(accuracy.median_error, 1)}<small>pos</small></strong></div>
            </div>
          </article>
        </section>

        <section className="perf-panels race-panels">
          <article className="perf-panel">
            <div className="panel-head">
              <span className="eyebrow">Cleanest Calls</span>
              <h2>Lowest Race MAE</h2>
            </div>
            <div className="race-error-list">
              {bestRaces.map(race => (
                <div className="race-error-row" key={`${race.year}-${race.round}`}>
                  <span>{raceLabel(race)}</span>
                  <strong>{fmt(race.mae, 2)}<small>pos</small></strong>
                </div>
              ))}
            </div>
          </article>

          <article className="perf-panel">
            <div className="panel-head">
              <span className="eyebrow">Hardest Calls</span>
              <h2>Highest Race MAE</h2>
            </div>
            <div className="race-error-list">
              {hardestRaces.map(race => (
                <div className="race-error-row hard" key={`${race.year}-${race.round}`}>
                  <span>{raceLabel(race)}</span>
                  <strong>{fmt(race.mae, 2)}<small>pos</small></strong>
                </div>
              ))}
            </div>
          </article>
        </section>
      </div>
    </main>
  );
}
