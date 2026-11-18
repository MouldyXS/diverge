import { copy, P0_NOTICE } from "../copy";

/** The P0 user notice (D14), verbatim, shown with every result. */
export function P0Notice() {
  return (
    <aside className="notice" aria-label={copy.p0Label}>
      {P0_NOTICE.map((paragraph) => (
        <p key={paragraph}>{paragraph}</p>
      ))}
    </aside>
  );
}
