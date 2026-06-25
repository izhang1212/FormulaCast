import { useEffect, useRef, useState } from "react";
import Header from "./components/Header";
import Home from "./views/Home";
import Predict from "./views/Predict";
import Replay from "./views/Replay";
import About from "./views/About";
import Performance from "./views/Performance";
import { getLivePredictions, getRefreshStatus, hasLiveBackend, startLocalModelRefresh } from "./api";

export default function App() {
  const [view, setView] = useState("home");
  const [dataVersion, setDataVersion] = useState(0);
  const completedRun = useRef("");

  useEffect(() => {
    if (!hasLiveBackend()) return undefined;

    if (import.meta.env.PROD) {
      // In production: call the lean live endpoint directly — no polling needed.
      // It runs a fresh Monte Carlo simulation and returns immediately.
      // If it fails (cold start timeout etc.), the page silently falls back
      // to the pre-built static prediction JSON served from the CDN.
      let active = true;
      getLivePredictions()
        .then(() => { if (active) setDataVersion(v => v + 1); })
        .catch(() => {});
      return () => { active = false; };
    }

    // Local dev: trigger a full rebuild and poll for completion.
    let active = true;
    let pollId = null;

    const applyStatus = status => {
      if (!active || !status) return;
      if (status.state === "succeeded" && status.finished_at !== completedRun.current) {
        completedRun.current = status.finished_at;
        setDataVersion(version => version + 1);
      }
      if (status.state === "succeeded" || status.state === "failed") {
        clearInterval(pollId);
      }
    };

    const poll = () => {
      getRefreshStatus()
        .then(applyStatus)
        .catch(() => { clearInterval(pollId); });
    };

    startLocalModelRefresh()
      .then(applyStatus)
      .catch(() => poll());

    pollId = setInterval(poll, 2500);

    return () => {
      active = false;
      clearInterval(pollId);
    };
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
