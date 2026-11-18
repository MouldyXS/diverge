import { useState, type KeyboardEvent } from "react";

import { copy } from "../copy";
import { exactValue, formatValue } from "../format";
import { distanceRange, scaleColor, type Matrix } from "./matrix";
import type { PairScoreOut } from "../api/types";

/** Up to this many words the values are written in the cells; above it the cells show color and the detail below. */
export const VALUES_IN_CELLS_UP_TO = 12;

interface Props {
  words: string[];
  matrix: Matrix;
  pairs: PairScoreOut[];
}

/**
 * A semantic table with one tab stop: arrows move a selected cell, whose detail is announced below. Every cell also
 * carries its value as text (visible up to 12 words, visually hidden above), and the pair table is the full alternative.
 */
export function DistanceMatrix({ words, matrix, pairs }: Props) {
  const n = words.length;
  const range = distanceRange(pairs);
  const compact = n > VALUES_IN_CELLS_UP_TO;
  const [selected, setSelected] = useState<[number, number] | null>(null);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const moves: Record<string, [number, number]> = { ArrowUp: [-1, 0], ArrowDown: [1, 0], ArrowLeft: [0, -1], ArrowRight: [0, 1] };
    const move = moves[event.key];
    if (!move) {
      return;
    }
    event.preventDefault();
    const [row, column] = selected ?? [0, n > 1 ? 1 : 0];
    if (selected === null) {
      setSelected([row, column]);
      return;
    }
    const clamp = (value: number) => Math.min(n - 1, Math.max(0, value));
    setSelected([clamp(row + move[0]), clamp(column + move[1])]);
  }

  let detail: string = copy.matrix.detailEmpty;
  if (selected !== null) {
    const [row, column] = selected;
    const value = matrix[row]?.[column];
    detail =
      value === null || value === undefined
        ? `${words[row]} — ${words[column]}: ${copy.matrix.diagonal}`
        : copy.matrix.detail(words[row]!, words[column]!, formatValue(value), exactValue(value));
  }

  return (
    <section className="matrix-region" aria-labelledby="matrix-heading">
      <h3 id="matrix-heading">{copy.matrix.heading}</h3>
      <div className="legend">
        <span>
          {copy.matrix.min} <span className="num">{formatValue(range.min)}</span>
        </span>
        <span className="legend__ramp" aria-hidden="true" />
        <span>
          {copy.matrix.max} <span className="num">{formatValue(range.max)}</span>
        </span>
        <span>{range.uniform ? copy.matrix.uniform : copy.matrix.scale}</span>
      </div>
      <p id="matrix-instructions" className="muted">
        {copy.matrix.instructions}
      </p>
      <div
        className="scroll matrix-grid"
        tabIndex={0}
        role="group"
        aria-label={copy.matrix.caption}
        aria-describedby="matrix-instructions"
        onKeyDown={onKeyDown}
      >
        <table className={`matrix${compact ? " matrix--compact" : ""}`}>
          <caption className="visually-hidden">{copy.matrix.caption}</caption>
          <thead>
            <tr>
              <td />
              {words.map((word, k) => (
                <th key={k} scope="col" title={word}>
                  <span aria-hidden="true">{k + 1}</span>
                  <span className="visually-hidden">{word}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, r) => (
              <tr key={r}>
                <th scope="row" title={words[r]}>
                  {compact ? (
                    <>
                      <span aria-hidden="true">{r + 1}</span>
                      <span className="visually-hidden">{words[r]}</span>
                    </>
                  ) : (
                    `${r + 1}. ${words[r]}`
                  )}
                </th>
                {row.map((value, c) => {
                  const isSelected = selected !== null && selected[0] === r && selected[1] === c;
                  if (value === null) {
                    return (
                      <td key={c} className={`matrix__diagonal${isSelected ? " matrix__selected" : ""}`} onClick={() => setSelected([r, c])}>
                        <span aria-hidden="true">—</span>
                        <span className="visually-hidden">{copy.matrix.diagonal}</span>
                      </td>
                    );
                  }
                  return (
                    <td
                      key={c}
                      className={isSelected ? "matrix__selected" : undefined}
                      style={{ background: scaleColor(value, range) }}
                      title={`${words[r]} — ${words[c]}: ${exactValue(value)}`}
                      onClick={() => setSelected([r, c])}
                    >
                      <span className={compact ? "visually-hidden" : undefined}>{formatValue(value)}</span>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="cell-detail" aria-live="polite">
        {detail}
      </p>
    </section>
  );
}
