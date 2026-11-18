import type { ModelRefOut } from "../api/types";
import { copy } from "../copy";

/** The model identity carried by a result. */
export function ModelBadge({ model }: { model: ModelRefOut }) {
  return (
    <dl className="kv model-panel">
      <dt>{copy.model.resultModel}</dt>
      <dd>
        <code>{model.model_id}</code>
      </dd>
      <dt>{copy.model.declaredRevision}</dt>
      <dd>
        <code>{model.declared_revision}</code>
      </dd>
      <dt>{copy.model.snapshotRevision}</dt>
      <dd>{model.snapshot_revision === null ? <span className="muted">{copy.model.notReported}</span> : <code>{model.snapshot_revision}</code>}</dd>
    </dl>
  );
}
