const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "");
const STATIC_BASE = "/predictions";

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  if (!res.ok) throw new Error(`Failed to load ${url}`);
  return res.json();
}

async function fetchPrediction(path, { optional = false } = {}) {
  let apiError = null;

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

export async function startLocalModelRefresh() {
  if (!API_BASE) return null;
  return fetchJson(`${API_BASE}/refresh/local`, { method: "POST" });
}

export async function getRefreshStatus() {
  if (!API_BASE) return null;
  return fetchJson(`${API_BASE}/refresh/status`);
}
