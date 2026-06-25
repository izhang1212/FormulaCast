import { useState, useEffect, useMemo } from "react";
import { useRaceIndex } from "../hooks/useRaces";
import { getRace } from "../api";
import { NAME, teamColor, withMeta } from "../config";
import RaceLights from "../components/RaceLights";
import Dropdown from "../components/Dropdown";
import CircuitSVG from "../components/CircuitSVG";

const DEFAULT_CARDS_VISIBLE = 3;
const SECONDS_PER_CARD = 2.2;

function getCardsVisible() {
    if (typeof window === "undefined") return DEFAULT_CARDS_VISIBLE;
    if (window.matchMedia("(max-width: 640px)").matches) return 1;
    if (window.matchMedia("(max-width: 900px)").matches) return 2;
    return DEFAULT_CARDS_VISIBLE;
}

function useCardsVisible() {
    const [cardsVisible, setCardsVisible] = useState(getCardsVisible);

    useEffect(() => {
        const update = () => setCardsVisible(getCardsVisible());
        window.addEventListener("resize", update);
        return () => window.removeEventListener("resize", update);
    }, []);

    return cardsVisible;
}

function cacheKey(race) {
    return `${race.year}-${race.round}`;
}

function CarouselCard({ summary, race }) {
    const details = race || withMeta(summary);
    const topDrivers = race?.drivers?.slice(0, 10) || [];
    const hasActuals = race?.drivers?.some(d => d.actual != null);
    const leader = topDrivers[0];
    const actualWinner = hasActuals
        ? race.drivers.find(d => d.actual === 1)
        : null;

    return (
        <article className="carousel-card">
            <div className="cc-top">
                <div>
                    <div className="cc-round">Round {summary.round} · {summary.year}</div>
                    <h3>{summary.name.replace(" Grand Prix", "")}</h3>
                    <div className="cc-loc">{details.loc}</div>
                </div>
                <CircuitSVG track={details.track} className="cc-circuit" />
            </div>
            <div className="cc-status">
                <span className={`pill ${hasActuals ? "official" : "sampled"}`}>
                    {hasActuals ? "Finished" : race ? "Prediction" : "Loading"}
                </span>
                {hasActuals
                    ? actualWinner && <strong>{actualWinner.driver} won</strong>
                    : leader && <strong>{leader.driver} {leader.win_pct.toFixed(1)}%</strong>
                }
            </div>
            <div className="cc-drivers">
                {topDrivers.length ? (
                    <>
                        {hasActuals && (
                            <div className="cc-col-header">
                                <span>Predicted</span>
                                <span>Actual</span>
                            </div>
                        )}
                        {topDrivers.map((driver, index) => (
                            <div className="cc-driver" key={driver.driver}>
                                <span className="cc-pos">{index + 1}</span>
                                <span className="tick" style={{ background: teamColor(summary.year, driver.driver) }} />
                                <span className="abbr">{driver.driver}</span>
                                <span className="full">{NAME[driver.driver] || ""}</span>
                                {hasActuals
                                    ? <span className="act">{driver.actual ?? "—"}</span>
                                    : <span className="pct">{driver.win_pct.toFixed(1)}%</span>
                                }
                            </div>
                        ))}
                    </>
                ) : (
                    <div className="cc-loading">Loading race forecast...</div>
                )}
            </div>
        </article>
    );
}

function Carousel() {
    const { years, byYear } = useRaceIndex();
    const [year, setYear] = useState(null);
    const [raceCache, setRaceCache] = useState({});
    const cardsVisible = useCardsVisible();

    const selectedYear = year ?? years[0] ?? null;
    const races = useMemo(
        () => selectedYear != null ? byYear(selectedYear) : [],
        [byYear, selectedYear]
    );
    const loopedRaces = useMemo(
        () => races.length ? [...races, ...races] : [],
        [races]
    );
    const slideStep = 100 / cardsVisible;
    const scrollDistance = races.length * slideStep;
    const scrollDuration = Math.max(races.length * SECONDS_PER_CARD, 18);

    useEffect(() => {
        if (!races.length) return;
        let active = true;
        const missing = races.filter(summary => !raceCache[cacheKey(summary)]);

        missing.forEach(summary => {
            const key = cacheKey(summary);
            getRace(summary.year, summary.round)
                .then(data => {
                    if (active) setRaceCache(cache => ({ ...cache, [key]: withMeta(data) }));
                })
                .catch(() => { });
        });

        return () => {
            active = false;
        };
    }, [races, raceCache]);

    if (!years.length) return null;

    return (
        <>
            <div className="shead"><span className="num">//</span><h2>Historical calls</h2>
                <span className="note">auto-scrolling · hover to inspect</span></div>
            <div className="carcontrols">
                <div className="ctl"><label>Season</label>
                    <Dropdown options={years.map(String)} value={String(selectedYear ?? "")}
                        onChange={v => setYear(Number(v))} />
                </div>
            </div>
            <div className="carousel-viewport">
                <div className="carousel-track" key={selectedYear}
                    style={{
                        "--scroll-distance": `-${scrollDistance}%`,
                        "--scroll-duration": `${scrollDuration}s`,
                        "--slide-size": `${slideStep}%`,
                    }}>
                    {loopedRaces.map((summary, index) => (
                        <div className="carousel-slide" key={`${summary.year}-${summary.round}-${index}`}>
                            <CarouselCard summary={summary} race={raceCache[cacheKey(summary)]} />
                        </div>
                    ))}
                </div>
            </div>
        </>
    );
}

export default function Home({ onNavigate }) {
    return (
        <section className="view show"><div className="wrap">
            <div className="hero">
                <div className="tag"><span className="dot" /> Random Forest + Monte Carlo · 2026 season</div>
                <RaceLights />
                <h1>Call the grid<br />before <span className="acc">lights out.</span></h1>
                <p className="sub">FormulaCast runs every Grand Prix ten thousand times — modelling pace,
                    chaos, and tire luck — to turn a race into a probability, not a guess.</p>
                <div className="modes">
                    <div className="mode predict" onClick={() => onNavigate("predict")}>
                        <span className="stripe" /><span className="edge" />
                        <div className="idx">01 / UPCOMING</div><h3>Predict the next races</h3>
                        <p>Forecast a Grand Prix that hasn't run yet. Before qualifying, the grid is sampled; after, the real order locks in.</p>
                        <span className="go">Open the paddock <span className="arr">→</span></span>
                    </div>
                    <div className="mode replay" onClick={() => onNavigate("replay")}>
                        <span className="stripe" /><span className="edge" />
                        <div className="idx">02 / FINISHED</div><h3>Replay a finished race</h3>
                        <p>Re-run a completed Grand Prix on its real starting grid and see how the model's call stacked up.</p>
                        <span className="go">Pick a race <span className="arr">→</span></span>
                    </div>
                </div>
            </div>
            <Carousel />
        </div></section>
    );
}
