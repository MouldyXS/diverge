import { copy } from "../copy";
import { formatValue } from "../format";

/** A distance placed on its fixed theoretical range [0, 2]. */
export function DistanceBar({ distance }: { distance: number }) {
  const percent = Math.min(100, Math.max(0, (distance / 2) * 100));
  return (
    <div className="distance-bar">
      <div className="distance-bar__track" role="img" aria-label={`${copy.pair.distance}: ${formatValue(distance)}. ${copy.pair.scale}.`}>
        <span className="distance-bar__marker" style={{ left: `${percent}%` }} />
      </div>
      <div className="distance-bar__ends" aria-hidden="true">
        <span>0</span>
        <span>1</span>
        <span>2</span>
      </div>
      <p className="muted">{copy.pair.scale}</p>
    </div>
  );
}
