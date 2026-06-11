const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") || (import.meta.env.PROD ? "/api" : "");
const STATIC_BASE = "/predictions";
let bootstrapPredictions = null;

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Failed to load ${url}`);
  return res.json();
}

async function fetchPrediction(path, { optional = false } = {}) {
  let apiError = null;
  const bootstrapped = readBootstrapPrediction(path);
  if (bootstrapped !== undefined) return bootstrapped;

  if (API_BASE) {
    try {
      return await fetchJson(`${API_BASE}/predictions${path}`);
    } catch (error) {
      apiError = error;
    }
  }

  try {
    return await fetchJson(`${STATIC_BASE}${path}`);
  } catch (staticError) {
    if (optional) return [];
    throw apiError || staticError;
  }
}

export async function getRaces() {
  return fetchPrediction("/races.json");
}

export async function getRace(year, round) {
  return fetchPrediction(`/${year}/round_${round}.json`);
}

export async function getFutureRaces() {
  return fetchPrediction("/future/index.json", { optional: true });
}

export async function getFutureRace(year, round) {
  return fetchPrediction(`/future/${year}_round_${round}.json`);
}

export async function getPerformance() {
  return fetchPrediction("/performance.json");
}

export function hasLiveBackend() {
  return Boolean(API_BASE);
}

function readBootstrapPrediction(path) {
  if (!bootstrapPredictions) return undefined;
  if (path === "/races.json") return bootstrapPredictions.racesIndex || [];
  if (path === "/future/index.json") return bootstrapPredictions.futureIndex || [];
  if (path === "/performance.json") return bootstrapPredictions.performance;

  const historical = path.match(/^\/(\d{4})\/round_(\d+)\.json$/);
  if (historical) return bootstrapPredictions.races?.[`${historical[1]}/round_${historical[2]}`];

  const future = path.match(/^\/future\/(\d{4})_round_(\d+)\.json$/);
  if (future) return bootstrapPredictions.future?.[`${future[1]}_round_${future[2]}`];

  return undefined;
}

export async function bootstrapLiveModel() {
  if (!API_BASE) return null;
  const payload = await fetchJson(`${API_BASE}/bootstrap`, { method: "POST" });
  bootstrapPredictions = payload.predictions;
  return payload.refresh;
}

export async function startLocalModelRefresh() {
  if (!API_BASE) return null;
  return fetchJson(`${API_BASE}/refresh/local`, { method: "POST" });
}

export async function getRefreshStatus() {
  if (!API_BASE) return null;
  return fetchJson(`${API_BASE}/refresh/status`);
}
