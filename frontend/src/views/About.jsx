import { STEPS } from "../config";

function Arrow({ dir }) {
    const line = dir === "a" ? "M25,3 C25,55 75,45 75,93" : "M75,3 C75,55 25,45 25,93";
    const head = dir === "a" ? "M66,84 L75,95 L84,84" : "M16,84 L25,95 L34,84";
    return (
        <div className="arrow">
            <svg viewBox="0 0 100 100" preserveAspectRatio="none">
                <path d={line} vectorEffect="non-scaling-stroke" />
                <path className="head" d={head} vectorEffect="non-scaling-stroke" />
            </svg>
        </div>
    );
}

export default function About() {
    return (
        <section className="view show"><div className="wrap">
            <div className="shead" style={{ borderTop: "none", marginTop: 34 }}>
                <span className="num">//</span><h2>How it works</h2><span className="note">data → forecast</span>
            </div>
            <p className="intro">FormulaCast turns historical race data into a probability for every driver.
                Each stage feeds the next — a learned model produces a single expected order, then a simulator
                turns that order into the full range of ways a race can actually play out.</p>
            <div className="flow">
                {STEPS.map((s, i) => (
                    <div key={s.t} style={{ display: "contents" }}>
                        <div className={`step ${i % 2 === 0 ? "left" : "right"}`}>
                            <div className="sidx">{i + 1}</div>
                            <span className="k">{s.k}</span><h3>{s.t}</h3><p>{s.d}</p>
                        </div>
                        {i < STEPS.length - 1 && <Arrow dir={i % 2 === 0 ? "a" : "b"} />}
                    </div>
                ))}
            </div>
        </div></section>
    );
}