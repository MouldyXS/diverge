import type { EntryIssue } from "../api/types";
import { copy } from "../copy";

/** The reasons of the entry at `position` (1-based), translated from their codes; nothing if it is valid. */
export function EntryErrors({ id, issues, position }: { id: string; issues: EntryIssue[]; position: number }) {
  const issue = issues.find((item) => item.position === position);
  if (!issue) {
    return null;
  }
  return (
    <ul id={id} className="field-error">
      {issue.reasons.map((reason) => (
        <li key={reason}>
          {copy.reasons[reason]}
          {reason === "exceeds_model_context" && issue.tokens !== null && issue.max_tokens !== null
            ? ` (${copy.tokens(issue.tokens, issue.max_tokens)})`
            : ""}
        </li>
      ))}
    </ul>
  );
}

export function hasIssue(issues: EntryIssue[], position: number): boolean {
  return issues.some((item) => item.position === position);
}
