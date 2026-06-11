import { useCallback, useEffect, useMemo, useState } from "react";
import { getRaces } from "../api";

export function useRaceIndex() {
  const [races, setRaces] = useState([]);

  useEffect(() => {
    let active = true;

    getRaces()
      .then(data => {
        if (active) setRaces(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        if (active) setRaces([]);
      });

    return () => {
      active = false;
    };
  }, []);

  const years = useMemo(
    () => [...new Set(races.map(race => race.year))].sort((a, b) => b - a),
    [races]
  );

  const racesByYear = useMemo(() => {
    return races.reduce((groups, race) => {
      if (!groups.has(race.year)) groups.set(race.year, []);
      groups.get(race.year).push(race);
      return groups;
    }, new Map());
  }, [races]);

  const byYear = useCallback(
    year => [...(racesByYear.get(Number(year)) || [])].sort((a, b) => a.round - b.round),
    [racesByYear]
  );

  return { races, years, byYear };
}
