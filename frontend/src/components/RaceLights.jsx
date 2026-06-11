import { useState, useEffect } from "react";

const COUNT = 5;

export default function RaceLights() {
  const [state, setState] = useState(Array(COUNT).fill(""));

  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setState(Array(COUNT).fill("on"));
      return;
    }
    let timers = [];
    const run = () => {
      setState(Array(COUNT).fill(""));
      for (let i = 0; i < COUNT; i++)
        timers.push(setTimeout(() => setState(s => { const n = [...s]; n[i] = "on"; return n; }), 300 + i * 260));
      timers.push(setTimeout(() => setState(Array(COUNT).fill("out")), 300 + COUNT * 260 + 650));
      timers.push(setTimeout(run, 300 + COUNT * 260 + 650 + 3200));
    };
    run();
    return () => timers.forEach(clearTimeout);
  }, []);

  return (
    <div className="lights">
      {state.map((s, i) => <div key={i} className={`light ${s}`} />)}
    </div>
  );
}