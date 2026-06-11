import { useState, useEffect } from "react";
import { getFutureRaces, getFutureRace } from "../api";
import { withMeta, TRACK_BY_NAME } from "../config";
import CircuitSVG from "../components/CircuitSVG";
import PredictionBoard from "../components/PredictionBoard";

function formatWeekend(raceDate) {
    if (!raceDate) return "";
    const race = new Date(`${raceDate.replace(" ", "T")}Z`);
    if (Number.isNaN(race.getTime())) return "";

    const start = new Date(race);
    start.setUTCDate(race.getUTCDate() - 2);
    const month = race.toLocaleString("en-US", { month: "short", timeZone: "UTC" }).toUpperCase();
    return `FRI-SUN · ${month} ${start.getUTCDate()}-${race.getUTCDate()}`;
}

function shortRaceName(name) {
    return name.replace(" Grand Prix", "").replace("Barcelona", "Barcelona");
}

export default function Predict() {
    const [list, setList] = useState(null);   // null = loading, [] = none exported
    const [active, setActive] = useState(null);
    const [race, setRace] = useState(null);

    useEffect(() => { getFutureRaces().then(setList).catch(() => setList([])); }, []);
    useEffect(() => { if (list?.length && !active) setActive(list[0]); }, [list, active]);
    useEffect(() => { if (active) getFutureRace(active.year, active.round).then(r => setRace(withMeta(r))); }, [active]);

    return (
        <section className="view show"><div className="wrap">
            <div className="shead" style={{ borderTop: "none", marginTop: 34 }}>
                <span className="num">01</span><h2>Upcoming races</h2>
                <span className="note">{list?.length ? `next ${list.length} on the calendar` : "next on the calendar"}</span>
            </div>
            <p className="intro">The Offical Grid is not yet available. Until qualifying sets the grid, FormulaCast
                samples a plausible starting order each simulation. Forecast accounts for where drivers might line up.
            </p>

            {list && list.length === 0 && (
                <div className="board" style={{ padding: 40, textAlign: "center", color: "var(--grey)" }}>
                    No upcoming-race predictions exported yet — run the future export to populate this view.
                </div>
            )}

            {list && list.length > 0 && (
                <>
                    <div className="races">
                        {list.map(r => (
                            <div className="racecard" key={`${r.year}-${r.round}`}>
                                <div className="top"><div className="rnd">Round {r.round}</div>
                                    <h3>{shortRaceName(r.name)}</h3>
                                    <div className="when">{formatWeekend(r.race_date)}</div></div>
                                <div className="map"><CircuitSVG track={TRACK_BY_NAME[r.name]} /></div>
                                <button className={`runbtn ${active?.year === r.year && active?.round === r.round ? "done" : ""}`} onClick={() => setActive(r)}>
                                    {active?.year === r.year && active?.round === r.round ? "Showing results ↓" : "Run prediction →"}
                                </button>
                            </div>
                        ))}
                    </div>
                    <div style={{ marginTop: 26 }}>{race && <PredictionBoard race={race} />}</div>
                </>
            )}
        </div></section>
    );
}
