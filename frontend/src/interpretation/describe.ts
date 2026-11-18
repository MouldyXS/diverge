// Turns the facts of a result into Spanish sentences, using the templates of copy.ts. Pure functions: nothing is
// recomputed here (the statistics come from the API) and every number is shown at four decimals, as everywhere else.
import type { InterpretationNote, PairRef, PairResponse, SetResponse } from "../api/types";
import { copy } from "../copy";
import { formatDisplayedDifference, formatValue } from "../format";

const T = copy.interpretation;

/** The two paragraphs that describe a pair, from the values `PairResponse` already carries. */
export function describePair(result: PairResponse): string[] {
  return [
    T.pair.lead(result.word_a, result.word_b, formatValue(result.similarity), formatValue(result.distance)),
    T.pair.definition,
  ];
}

/** The warning shown apart from the sentences of a pair. */
export const PAIR_NOTE = T.pair.note;

function label(words: string[], ref: PairRef): string {
  return T.set.pairLabel(words[ref.i] ?? "?", words[ref.j] ?? "?");
}

/** Listed pairs, with the rest of the tie as a count ("y 7 más"): the sentence stays short for any set size. */
function listPairs(words: string[], refs: PairRef[], total: number): string {
  const labels = refs.map((ref) => label(words, ref));
  const more = total - labels.length;
  return more > 0 ? T.set.andMore(labels, more) : T.set.join(labels);
}

/** The sentences that describe a set: size, mean, extremes (with ties) and the relation of the pairs to the mean. */
export function describeSet(result: SetResponse): string[] {
  const it = result.interpretation;
  const flags = new Set(it.flags);
  const min = formatValue(it.min_distance);
  const max = formatValue(it.max_distance);
  const sentences = [T.set.compared(result.n_pairs, result.n_words), T.set.mean(formatValue(result.mean_distance))];

  if (flags.has("single_pair")) {
    return [...sentences, T.set.single(min)];
  }
  if (flags.has("all_equal_at_precision")) {
    return [...sentences, T.set.allEqual(min, flags.has("all_exactly_equal"))];
  }

  // The range is the difference of the extremes as shown (0,3495 - 0,1815 = 0,1680), not the exact range rounded.
  sentences.push(T.set.range(min, max, formatDisplayedDifference(it.max_distance, it.min_distance)));
  const lowest = it.min_pairs[0];
  const highest = it.max_pairs[0];
  const lowestTie = flags.has("tie_at_min");
  const highestTie = flags.has("tie_at_max");
  if (!lowestTie && !highestTie && lowest && highest) {
    sentences.push(T.set.extremes(label(result.words, lowest), label(result.words, highest)));
  } else {
    if (lowest) {
      sentences.push(
        lowestTie
          ? T.set.lowestTie(it.n_min_pairs, min, flags.has("exact_tie_at_min"), listPairs(result.words, it.min_pairs, it.n_min_pairs))
          : T.set.lowestAlone(label(result.words, lowest)),
      );
    }
    if (highest) {
      sentences.push(
        highestTie
          ? T.set.highestTie(it.n_max_pairs, max, flags.has("exact_tie_at_max"), listPairs(result.words, it.max_pairs, it.n_max_pairs))
          : T.set.highestAlone(label(result.words, highest)),
      );
    }
  }
  sentences.push(T.set.relative(it.n_above_mean, it.n_below_mean, it.n_at_mean));
  return sentences;
}

/** The warnings of a set, by code, in the order the API sends them. */
export function setNotes(notes: InterpretationNote[]): string[] {
  return notes.map((code) => T.notes[code]);
}
