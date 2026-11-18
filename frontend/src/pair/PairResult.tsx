import type { PairResponse } from "../api/types";
import { DistanceBar } from "../components/DistanceBar";
import { ModelBadge } from "../components/ModelBadge";
import { P0Notice } from "../components/P0Notice";
import { copy } from "../copy";
import { exactValue, formatValue } from "../format";
import { PairInterpretation } from "../interpretation/PairInterpretation";

export function PairResult({ result }: { result: PairResponse }) {
  return (
    <section className="card" aria-labelledby="pair-result-heading">
      <h3 id="pair-result-heading">{copy.pair.resultHeading}</h3>
      <ul className="words" aria-label={copy.set.words}>
        <li>{result.word_a}</li>
        <li>{result.word_b}</li>
      </ul>
      <div className="metrics">
        <div className="metric">
          <span className="metric__label">{copy.pair.similarity}</span>
          <span className="metric__value" title={exactValue(result.similarity)}>
            {formatValue(result.similarity)}
          </span>
        </div>
        <div className="metric">
          <span className="metric__label">{copy.pair.distance}</span>
          <span className="metric__value" title={exactValue(result.distance)}>
            {formatValue(result.distance)}
          </span>
        </div>
      </div>
      <DistanceBar distance={result.distance} />
      <PairInterpretation result={result} />
      <ModelBadge model={result.model} />
      <P0Notice />
    </section>
  );
}
