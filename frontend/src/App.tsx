import { useRef, useState, type KeyboardEvent } from "react";

import { BackendStatus } from "./backend/BackendStatus";
import { ModelPanel } from "./backend/ModelPanel";
import { copy } from "./copy";
import { PairAnalysis } from "./pair/PairAnalysis";
import { SetAnalysis } from "./set/SetAnalysis";

const TABS = [
  { id: "pair", label: copy.app.tabPair },
  { id: "set", label: copy.app.tabSet },
] as const;
type TabId = (typeof TABS)[number]["id"];

/** Layout and the two analysis modes. Both panels stay mounted, so each keeps its entries during the session. */
export function App() {
  const [active, setActive] = useState<TabId>("pair");
  const buttons = useRef<(HTMLButtonElement | null)[]>([]);

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const index = TABS.findIndex((tab) => tab.id === active);
    const targets: Record<string, number> = {
      ArrowRight: (index + 1) % TABS.length,
      ArrowLeft: (index - 1 + TABS.length) % TABS.length,
      Home: 0,
      End: TABS.length - 1,
    };
    const next = targets[event.key];
    if (next === undefined) {
      return;
    }
    event.preventDefault();
    setActive(TABS[next]!.id);
    buttons.current[next]?.focus();
  }

  return (
    <div className="page">
      <header className="header">
        <div className="header__title">
          <h1>{copy.app.title}</h1>
          <p className="muted">{copy.app.subtitle}</p>
          <p className="muted local-note">{copy.app.local}</p>
          <ModelPanel />
        </div>
        <BackendStatus />
      </header>
      <main>
        <div className="tabs" role="tablist" aria-label={copy.app.tabsLabel} onKeyDown={onKeyDown}>
          {TABS.map((tab, k) => (
            <button
              key={tab.id}
              ref={(element) => {
                buttons.current[k] = element;
              }}
              id={`tab-${tab.id}`}
              type="button"
              role="tab"
              className="tab"
              aria-selected={active === tab.id}
              aria-controls={`panel-${tab.id}`}
              tabIndex={active === tab.id ? 0 : -1}
              onClick={() => setActive(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div id="panel-pair" role="tabpanel" aria-labelledby="tab-pair" hidden={active !== "pair"} className="panel">
          <PairAnalysis />
        </div>
        <div id="panel-set" role="tabpanel" aria-labelledby="tab-set" hidden={active !== "set"} className="panel">
          <SetAnalysis />
        </div>
      </main>
    </div>
  );
}
