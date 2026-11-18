import type { SetResponse } from "../api/types";
import { copy } from "../copy";
import { describeSet, setNotes } from "./describe";

/** Descriptive reading of a set, from the `interpretation` facts of `/sets`. It does not replace the matrix or the table. */
export function SetInterpretationPanel({ result }: { result: SetResponse }) {
  return (
    <section className="reading" aria-labelledby="set-reading-heading">
      <h3 id="set-reading-heading">{copy.interpretation.heading}</h3>
      {describeSet(result).map((sentence) => (
        <p key={sentence}>{sentence}</p>
      ))}
      <div className="reading__notes">
        <p className="reading__notes-title">{copy.interpretation.howToRead}</p>
        <ul>
          {setNotes(result.interpretation.notes).map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
