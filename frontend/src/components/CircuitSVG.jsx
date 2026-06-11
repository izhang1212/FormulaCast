import { TRACK } from "../config";

export default function CircuitSVG({ track, className }) {
  const d = TRACK[track];
  return (
    <svg viewBox="0 0 200 120" className={className}>
      {d && <path d={d} />}
    </svg>
  );
}