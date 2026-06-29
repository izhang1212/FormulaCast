import { useEffect, useState } from "react";
import Header from "./components/Header";
import Home from "./views/Home";
import Predict from "./views/Predict";
import Replay from "./views/Replay";
import About from "./views/About";
import Performance from "./views/Performance";
import { getLivePredictions, hasLiveBackend } from "./api";

export default function App() {
  const [view, setView] = useState("home");
  const [dataVersion, setDataVersion] = useState(0);

  useEffect(() => {
    if (!hasLiveBackend()) return undefined;

    // Call the live endpoint — it downloads the pre-built RF model + feature rows
    // from Supabase (or falls back to local season files), then runs a fresh
    // Monte Carlo simulation. seed=None means every visitor gets unique results.
    // Falls back silently to the pre-built static JSON if this fails.
    let active = true;
    getLivePredictions()
      .then(() => { if (active) setDataVersion(v => v + 1); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  return (
    <>
      <Header view={view} onNavigate={setView} />
      {view === "home" && <Home key={`home-${dataVersion}`} onNavigate={setView} />}
      {view === "predict" && <Predict key={`predict-${dataVersion}`} />}
      {view === "replay" && <Replay key={`replay-${dataVersion}`} />}
      {view === "performance" && <Performance key={`performance-${dataVersion}`} />}
      {view === "about" && <About />}
    </>
  );
}
