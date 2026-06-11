import { useState, useEffect, useMemo } from "react";
import { useRaceIndex } from "../hooks/useRaces";
import { getRace } from "../api";
import { withMeta } from "../config";
import Dropdown from "../components/Dropdown";
import PredictionBoard from "../components/PredictionBoard";
import AccuracyBoard from "../components/AccuracyBoard";

export default function Replay() {
    const { years, byYear } = useRaceIndex();
    const [year, setYear] = useState(null);
    const [round, setRound] = useState(null);
    const [race, setRace] = useState(null);

    useEffect(() => { if (years.length && year == null) setYear(years[0]); }, [years]);
    const races = year != null ? byYear(year) : [];
    useEffect(() => { if (races.length) setRound(races[0].round); }, [year]); // eslint-disable-line
    useEffect(() => {
        if (year != null && round != null) getRace(year, round).then(r => setRace(withMeta(r)));
    }, [year, round]);

    const hasActuals = race?.drivers?.some(d => d.actual != null);
    const activeIndex = races.findIndex(r => r.round === round);
    const activeRace = activeIndex >= 0 ? races[activeIndex] : null;
    const raceOptions = useMemo(
        () => races.map(r => `R${String(r.round).padStart(2, "0")} · ${r.name.replace(" Grand Prix", "")}`),
        [races]
    );
    const raceValue = activeRace
        ? `R${String(activeRace.round).padStart(2, "0")} · ${activeRace.name.replace(" Grand Prix", "")}`
        : "";

    const selectRace = (value) => {
        const next = races[raceOptions.indexOf(value)];
        if (next) setRound(next.round);
    };

    const stepRace = (direction) => {
        if (!races.length) return;
        const current = activeIndex >= 0 ? activeIndex : 0;
        const next = (current + direction + races.length) % races.length;
        setRound(races[next].round);
    };

    return (
        <section className="view show"><div className="wrap">
            <div className="shead" style={{ borderTop: "none", marginTop: 34 }}>
                <span className="num">02</span><h2>Replay a race</h2>
                <span className="note">{years.length ? `${years[years.length - 1]}–${years[0]}` : ""}</span>
            </div>
            <p className="intro">Pick a season, then a Grand Prix. The model re-runs it on the real starting grid
                {hasActuals ? ", then scores its predicted order against what actually happened." : "."}</p>
            <div className="controls">
                <div className="ctl"><label>Season</label>
                    <Dropdown options={years.map(String)} value={String(year ?? "")} onChange={v => setYear(Number(v))} />
                </div>
                <div className="ctl race-ctl"><label>Grand Prix</label>
                    <Dropdown options={raceOptions} value={raceValue} onChange={selectRace} />
                </div>
                <div className="race-stepper">
                    <button className="cbtn" onClick={() => stepRace(-1)} aria-label="Previous race">‹</button>
                    <span>{activeRace ? `Round ${activeRace.round} of ${races.length}` : "Round -"}</span>
                    <button className="cbtn" onClick={() => stepRace(1)} aria-label="Next race">›</button>
                </div>
            </div>
            {race && (hasActuals ? <AccuracyBoard race={race} /> : <PredictionBoard race={race} />)}
        </div></section>
    );
}
