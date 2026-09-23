import { useMemo, useState } from "react";
import { CompoundMatrix } from "./components/CompoundMatrix";
import { ResultPanel } from "./components/ResultPanel";
import { ReviewPanel } from "./components/ReviewPanel";
import { solveBalance } from "./api";
import type { BalanceResponse, Compound } from "./types";
import { validateCompounds } from "./validation";

const INITIAL_COMPOUNDS: Compound[] = [
  { id: "", role: "REACTANT", composition: [{ symbol: "", count: "" }] },
  { id: "", role: "PRODUCT", composition: [{ symbol: "", count: "" }] },
];

interface CertifiedSnapshot {
  result: BalanceResponse;
  /** Deep copy of the exact compounds the certificate was issued for; the
   *  result panel keeps showing these even while the editor changes. */
  compounds: Compound[];
  /** Edit epoch locked in at solve time. The certificate is valid only while
   *  the live epoch equals this — a single keystroke revokes it. */
  epoch: number;
}

export default function App() {
  const [compounds, setCompounds] = useState<Compound[]>(INITIAL_COMPOUNDS);
  const [snapshot, setSnapshot] = useState<CertifiedSnapshot | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  // Monotonic counter bumped on every editor mutation.
  const [editEpoch, setEditEpoch] = useState(0);

  const issues = useMemo(() => validateCompounds(compounds), [compounds]);

  const handleChange = (next: Compound[]) => {
    setCompounds(next);
    setEditEpoch((epoch) => epoch + 1);
  };

  const handleSolve = async () => {
    if (issues.length > 0) return;
    setBusy(true);
    setError(null);
    try {
      const result = await solveBalance(compounds);
      setSnapshot({
        result,
        compounds: cloneCompounds(compounds),
        epoch: editEpoch,
      });
    } catch (err) {
      // Whole-document rejection from the authoritative server validation.
      setError(err instanceof Error ? err.message : "求解失败");
      setSnapshot(null);
    } finally {
      setBusy(false);
    }
  };

  const certificateStale = snapshot !== null && snapshot.epoch !== editEpoch;

  const suggested = useMemo(() => {
    if (snapshot?.result.status !== "BALANCED") return {};
    return Object.fromEntries(
      snapshot.result.coefficients!.map((entry) => [entry.id, entry.coefficient])
    );
  }, [snapshot]);

  return (
    <main className="app-shell">
      <header>
        <h1>化学方程式精确配平工作台</h1>
        <p className="dim">
          有理数高斯消元 · 零空间精确判定 · 唯一原始整数配方或明确的不可认证原因
        </p>
      </header>

      <CompoundMatrix compounds={compounds} onChange={handleChange} />

      <section className="panel" data-testid="control-panel">
        <h2>② 求解与认证</h2>
        {issues.length > 0 && (
          <ul className="issue-list" data-testid="issue-list">
            {issues.map((issue, i) => (
              <li key={i}>{issue.message}</li>
            ))}
          </ul>
        )}
        <button
          type="button"
          className="primary big"
          data-testid="solve-button"
          onClick={handleSolve}
          disabled={busy || issues.length > 0}
        >
          {busy ? "精确消元中…" : "求解并签发证书"}
        </button>
        {error && (
          <div className="error-text" data-testid="solve-error">
            整份请求被拒绝：{error}
          </div>
        )}
      </section>

      {snapshot && (
        <ResultPanel
          result={snapshot.result}
          compounds={snapshot.compounds}
          certificateStale={certificateStale}
        />
      )}

      {snapshot && (
        <ReviewPanel
          key={`${snapshot.epoch}-${snapshot.result.certificate.certificateId}`}
          compounds={compounds}
          suggested={suggested}
          editEpoch={editEpoch}
        />
      )}

      <footer className="dim small">
        任何输入修改都会立即撤销旧证书；只有指纹匹配、可逐项验算的唯一配方才被认证。
      </footer>
    </main>
  );
}

function cloneCompounds(value: Compound[]): Compound[] {
  return value.map((compound) => ({
    id: compound.id,
    role: compound.role,
    composition: compound.composition.map((entry) => ({ ...entry })),
  }));
}
