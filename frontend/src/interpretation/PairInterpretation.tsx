import type { PairResponse } from "../api/types";
import { copy } from "../copy";
import { describePair, PAIR_NOTE } from "./describe";

/** Descriptive reading of a pair, built in the browser from the values the API already returned. */
export function PairInterpretation({ result }: { result: PairResponse }) {
  return (
    <section className="reading" aria-labelledby="pair-reading-heading">
      <h3 id="pair-reading-heading">{copy.interpretation.heading}</h3>
      {describePair(result).map((sentence) => (
        <p key={sentence}>{sentence}</p>
      ))}
      <div className="reading__notes">
        <p className="reading__notes-title">{copy.interpretation.howToRead}</p>
        <ul>
          <li>{PAIR_NOTE}</li>
        </ul>
      </div>
    </section>
  );
}
