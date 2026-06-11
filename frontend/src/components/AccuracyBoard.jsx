import { NAME, teamColor } from "../config";
import CircuitSVG from "./CircuitSVG";

export default function AccuracyBoard({ race, limit }) {
  const ranked = race.drivers
    .map((driver, index) => ({ driver, index }))
    .sort((a, b) => a.driver.expected_position - b.driver.expected_position || a.index - b.index)
    .reduce((ranks, entry, rankIndex) => {
      ranks[entry.driver.driver] = rankIndex + 1;
      return ranks;
    }, {});
  const rows = limit ? race.drivers.slice(0, limit) : race.drivers;
  const errs = race.drivers.filter(d => d.actual != null)
    .map(d => Math.abs(d.expected_position - d.actual));
  const mae = errs.length ? errs.reduce((a, b) => a + b, 0) / errs.length : 0;
  const w3 = errs.length ? Math.round(errs.filter(e => e <= 3).length / errs.length * 100) : 0;

  return (
    <div className="board">
      <div className="bhead">
        <CircuitSVG track={race.track} className="circuit" />
        <div className="meta"><h4>{race.name}</h4><div className="loc">{race.loc}</div></div>
        <span className="pill official">Official grid</span>
      </div>
      <div className="cols acc"><span>#</span><span>Driver</span><span>P Rank</span><span>Pred</span><span>Actual</span><span>Err</span></div>
      {rows.map((d, i) => {
        const dnf = d.actual == null;
        const e = dnf ? null : Math.abs(d.expected_position - d.actual);
        const cls = dnf ? "bad" : e <= 1.5 ? "good" : e <= 3.5 ? "mid" : "bad";
        return (
          <div className="row acc" key={d.driver}>
            <div className="pos">{i + 1}</div>
            <div className="drv">
              <span className="tick" style={{ background: teamColor(race.year, d.driver) }} />
              <span className="abbr">{d.driver}</span>
              <span className="full">{NAME[d.driver] || ""}</span>
            </div>
            <div className="rank">{ranked[d.driver]}</div>
            <div className="epos">{d.expected_position.toFixed(1)}</div>
            <div className="act">{dnf ? "DNF" : "P" + d.actual}</div>
            <div className={`err ${cls}`}>{dnf ? "DNF" : e.toFixed(1)}</div>
          </div>
        );
      })}
      <div className="bfoot">
        <div className="stat"><span className="k">Mean abs error</span><span className="v">{mae.toFixed(2)} <small>pos</small></span></div>
        <div className="stat"><span className="k">Within 3</span><span className="v">{w3}<small>%</small></span></div>
        <div className="stat"><span className="k">Grid</span>
          <span className="v" style={{ color: "#36d399", fontSize: 16, letterSpacing: ".05em" }}>OFFICIAL</span></div>
      </div>
    </div>
  );
}
