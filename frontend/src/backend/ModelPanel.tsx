import type { ReactNode } from "react";

import { copy } from "../copy";
import { useBackend } from "./BackendProvider";

function orNotReported(value: string | number | null | undefined): ReactNode {
  return value === null || value === undefined ? <span className="muted">{copy.model.notReported}</span> : String(value);
}

export function ModelPanel() {
  const { model } = useBackend();
  if (model === null) {
    return null;
  }
  const versions = Object.entries(model.versions)
    .filter(([, version]) => version !== null)
    .map(([name, version]) => `${name} ${version}`)
    .join(" · ");
  return (
    <details className="model-panel">
      <summary>
        {copy.model.summary}: <code>{model.model_id}</code>
      </summary>
      <dl>
        <dt>{copy.model.modelId}</dt>
        <dd>
          <code>{model.model_id}</code>
        </dd>
        <dt>{copy.model.declaredRevision}</dt>
        <dd>
          <code>{model.declared_revision}</code>
        </dd>
        <dt>{copy.model.snapshotRevision}</dt>
        <dd>
          {model.snapshot_revision === null ? orNotReported(null) : <code>{model.snapshot_revision}</code>}
          <br />
          <span className="muted">{copy.model.snapshotNote}</span>
        </dd>
        <dt>{copy.model.dimension}</dt>
        <dd className="num">{orNotReported(model.embedding_dimension)}</dd>
        <dt>{copy.model.pooling}</dt>
        <dd>{orNotReported(model.pooling_mode)}</dd>
        <dt>{copy.model.maxInputTokens}</dt>
        <dd className="num">{model.limits.max_input_tokens}</dd>
        <dt>{copy.model.maxWords}</dt>
        <dd className="num">{model.limits.max_words}</dd>
        <dt>{copy.model.device}</dt>
        <dd>
          {orNotReported(model.device)} · {orNotReported(model.dtype)}
        </dd>
        <dt>{copy.model.attention}</dt>
        <dd>{orNotReported(model.attention_implementation)}</dd>
        <dt>{copy.model.offline}</dt>
        <dd>{model.offline === null ? orNotReported(null) : model.offline ? copy.model.yes : copy.model.no}</dd>
        <dt>{copy.model.versions}</dt>
        <dd>{versions || orNotReported(null)}</dd>
        <dt>{copy.model.apiVersion}</dt>
        <dd>{model.api_version}</dd>
      </dl>
    </details>
  );
}
