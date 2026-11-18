import type { PairScoreOut, SetResponse } from "../api/types";
import { ModelBadge } from "../components/ModelBadge";
import { P0Notice } from "../components/P0Notice";
import { copy } from "../copy";
import { exactValue, formatValue } from "../format";
import { SetInterpretationPanel } from "../interpretation/SetInterpretationPanel";
import { DistanceMatrix } from "./DistanceMatrix";
import { buildMatrix, MatrixIntegrityError, type Matrix } from "./matrix";
import { PairTable } from "./PairTable";

function Extreme({ label, pair }: { label: string; pair: PairScoreOut }) {
  return (
    <div className="metric">
      <span className="metric__label">{label}</span>
      <span>
        {pair.word_i} — {pair.word_j}
      </span>
      <span className="num" title={exactValue(pair.distance)}>
        {copy.pairs.distance}: {formatValue(pair.distance)}
      </span>
    </div>
  );
}

export function SetResults({ result }: { result: SetResponse }) {
  let matrix: Matrix | null = null;
  try {
    matrix = buildMatrix(result);
  } catch (error) {
    if (!(error instanceof MatrixIntegrityError)) {
      throw error;
    }
  }
  return (
    <section className="card" aria-labelledby="set-result-heading">
      <h3 id="set-result-heading">{copy.set.resultHeading}</h3>
      <ol className="words" aria-label={copy.set.words}>
        {result.words.map((word, k) => (
          <li key={k}>
            <span className="muted num">{k + 1}.</span> {word}
          </li>
        ))}
      </ol>
      <div className="metrics">
        <div className="metric">
          <span className="metric__label">{copy.set.nWords}</span>
          <span className="metric__value">{result.n_words}</span>
        </div>
        <div className="metric">
          <span className="metric__label">{copy.set.nPairs}</span>
          <span className="metric__value">{result.n_pairs}</span>
        </div>
        <div className="metric">
          <span className="metric__label">{copy.set.mean}</span>
          <span className="metric__value" title={exactValue(result.mean_distance)}>
            {formatValue(result.mean_distance)}
          </span>
          <span className="muted">{copy.set.meanNote}</span>
        </div>
      </div>
      <div className="metrics">
        <Extreme label={copy.set.closest} pair={result.closest} />
        <Extreme label={copy.set.mostDistant} pair={result.most_distant} />
      </div>
      <SetInterpretationPanel result={result} />
      {matrix === null ? (
        <p role="alert" className="field-error">
          {copy.matrix.integrity}
        </p>
      ) : (
        <DistanceMatrix words={result.words} matrix={matrix} pairs={result.pairs} />
      )}
      <PairTable pairs={result.pairs} />
      <ModelBadge model={result.model} />
      <P0Notice />
    </section>
  );
}
