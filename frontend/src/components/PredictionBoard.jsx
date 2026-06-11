import { useState, useEffect } from "react";
import { NAME, teamColor } from "../config";
import CircuitSVG from "./CircuitSVG";

export default function PredictionBoard({ race, limit }) {
  const [ready, setReady] = useState(false);
  useEffect(() => {
    setReady(false);
    const id = requestAnimationFrame(() => setReady(true));
    return () => cancelAnimationFrame(id);
  }, [race]);

  const ranked = race.drivers
    .map((driver, index) => ({ driver, index }))
    .sort((a, b) => a.driver.expected_position - b.driver.expected_position || a.index - b.index)
    .reduce((ranks, entry, rankIndex) => {
      ranks[entry.driver.driver] = rankIndex + 1;
      return ranks;
    }, {});
  const rows = limit ? race.drivers.slice(0, limit) : race.drivers;
  const max = Math.max(...rows.map(r => r.win_pct), 1);
  const fav = rows[0];
  const podiumFav = race.drivers.reduce((best, driver) => (
    (driver.podium_pct ?? 0) > (best.podium_pct ?? 0) ? driver : best
  ), fav);
  const pointsLeader = race.drivers.reduce((best, driver) => (
    (driver.expected_points ?? 0) > (best.expected_points ?? 0) ? driver : best
  ), fav);
  const official = race.mode === "official";
  const pct = value => value == null ? "-" : `${value.toFixed(1)}%`;
  const num = value => value == null ? "-" : value.toFixed(1);

  return (
    <div className="board">
      <div className="bhead">
        <CircuitSVG track={race.track} className="circuit" />
        <div className="meta"><h4>{race.name}</h4><div className="loc">{race.loc}</div></div>
        <span className={`pill ${official ? "official" : "sampled"}`}>
          {official ? "Official grid" : "Pre-qualifying · sampled grid"}
        </span>
      </div>
      <div className="cols pred">
        <span>P</span><span>Driver</span><span>P Rank</span><span>Win prob</span><span>Podium</span><span>E[pos]</span><span>xPts</span>
      </div>
      {rows.map((d, i) => (
        <div className={`row pred ${ranked[d.driver] === 1 ? "lead" : ""}`} key={d.driver}>
          <div className="pos">{i + 1}</div>
          <div className="drv">
            <span className="tick" style={{ background: teamColor(race.year, d.driver) }} />
            <span className="abbr">{d.driver}</span>
            <span className="full">{NAME[d.driver] || ""}</span>
          </div>
          <div className="rank">{ranked[d.driver]}</div>
          <div className="barwrap">
            <span className="bar"><i style={{ width: ready ? `${(d.win_pct / max) * 100}%` : 0 }} /></span>
            <span className="val">{pct(d.win_pct)}</span>
          </div>
          <div className="podium">{pct(d.podium_pct)}</div>
          <div className="epos">{num(d.expected_position)}</div>
          <div className="xpts">{num(d.expected_points)}</div>
        </div>
      ))}
      <div className="bfoot">
        <div className="stat"><span className="k">Sims</span><span className="v">10,000</span></div>
        <div className="stat"><span className="k">Win favourite</span><span className="v">{fav.driver} <small>{pct(fav.win_pct)}</small></span></div>
        <div className="stat"><span className="k">Podium favourite</span><span className="v">{podiumFav.driver} <small>{pct(podiumFav.podium_pct)}</small></span></div>
        <div className="stat"><span className="k">Expected points</span><span className="v">{pointsLeader.driver} <small>{num(pointsLeader.expected_points)}</small></span></div>
        <div className="stat"><span className="k">Grid</span>
          <span className="v" style={{ color: official ? "#36d399" : "var(--yellow)", fontSize: 16, letterSpacing: ".05em" }}>
            {official ? "OFFICIAL" : "SAMPLED"}
          </span></div>
      </div>
    </div>
  );
}
