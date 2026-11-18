import { useState } from "react";

import type { PairScoreOut } from "../api/types";
import { copy } from "../copy";
import { exactValue, formatValue } from "../format";

type Sort = "none" | "ascending" | "descending";
const NEXT: Record<Sort, Sort> = { none: "ascending", ascending: "descending", descending: "none" };
const LABEL: Record<Sort, string> = { none: copy.pairs.sortNone, ascending: copy.pairs.sortAsc, descending: copy.pairs.sortDesc };

/** Every pair, the accessible alternative to the matrix. Sorting works on a copy; the result is not changed. */
export function PairTable({ pairs }: { pairs: PairScoreOut[] }) {
  const [sort, setSort] = useState<Sort>("none");
  const indexed = pairs.map((pair, order) => ({ pair, order }));
  const rows =
    sort === "none"
      ? indexed
      : [...indexed].sort((x, y) => (sort === "ascending" ? 1 : -1) * (x.pair.distance - y.pair.distance) || x.order - y.order);
  return (
    <section aria-labelledby="pairs-heading">
      <h3 id="pairs-heading">{copy.pairs.heading}</h3>
      <div className="scroll">
        <table className="pairs-table">
          <thead>
            <tr>
              <th scope="col" className="num">
                {copy.pairs.order}
              </th>
              <th scope="col">{copy.pairs.first}</th>
              <th scope="col">{copy.pairs.second}</th>
              <th scope="col" className="num">
                {copy.pairs.similarity}
              </th>
              <th scope="col" className="num" aria-sort={sort}>
                <button type="button" className="sort-button" onClick={() => setSort(NEXT[sort])}>
                  {copy.pairs.distance}
                  <span className="visually-hidden">
                    {" "}
                    · {copy.pairs.sortBy}: {LABEL[sort]}
                  </span>
                  <span aria-hidden="true">{sort === "ascending" ? " ↑" : sort === "descending" ? " ↓" : ""}</span>
                </button>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map(({ pair, order }) => (
              <tr key={`${pair.i}-${pair.j}`}>
                <td className="num">{order + 1}</td>
                <td>
                  <span className="muted num">{pair.i + 1}.</span> {pair.word_i}
                </td>
                <td>
                  <span className="muted num">{pair.j + 1}.</span> {pair.word_j}
                </td>
                <td className="num" title={exactValue(pair.similarity)}>
                  {formatValue(pair.similarity)}
                </td>
                <td className="num" title={exactValue(pair.distance)}>
                  {formatValue(pair.distance)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
