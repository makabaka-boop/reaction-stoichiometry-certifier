import type { BalanceResponse, Compound } from "../types";

interface Props {
  result: BalanceResponse;
  compounds: Compound[];
  certificateStale: boolean;
}

const STATUS_TEXT: Record<BalanceResponse["status"], { title: string; tone: string }> = {
  BALANCED: { title: "唯一原始配方已认证", tone: "ok" },
  NO_BALANCE: { title: "不可认证：无守恒解（NO_BALANCE）", tone: "bad" },
  UNDERDETERMINED: {
    title: "不可认证：体系欠定，存在多解（UNDERDETERMINED）",
    tone: "warn",
  },
  NO_POSITIVE_BALANCE: {
    title: "不可认证：无全正系数（NO_POSITIVE_BALANCE）",
    tone: "bad",
  },
};

export function ResultPanel({ result, compounds, certificateStale }: Props) {
  const meta = STATUS_TEXT[result.status];

  const coefficientMap = new Map(
    (result.coefficients ?? []).map((entry) => [entry.id, entry.coefficient])
  );

  const reactants = compounds.filter((c) => c.role === "REACTANT");
  const products = compounds.filter((c) => c.role === "PRODUCT");
  const term = (compound: Compound) => {
    const coefficient = coefficientMap.get(compound.id);
    return coefficient === undefined
      ? compound.id
      : `${coefficient === 1 ? "" : coefficient} ${compound.id}`;
  };

  return (
    <section className={`panel tone-${meta.tone}`} data-testid="result-panel">
      <h2>③ 精确求解结果</h2>
      <p className={`status-banner ${meta.tone}`} data-testid="status-banner">
        {meta.title}
      </p>
      <p className="dim" data-testid="nullity">
        零空间维数（精确有理数消元）：{result.nullity}
        {result.reason ? `　·　判定依据：${result.reason}` : ""}
      </p>

      {result.status === "BALANCED" && result.coefficients && (
        <>
          <div className="equation" data-testid="balanced-equation">
            {reactants.map(term).join(" ＋ ") || "（无反应物）"}
            <span className="arrow">　⟶　</span>
            {products.map(term).join(" ＋ ") || "（无产物）"}
          </div>

          <table className="totals-table" data-testid="totals-table">
            <thead>
              <tr>
                <th>元素</th>
                <th>反应物侧总数</th>
                <th>产物侧总数</th>
                <th>逐项验算</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(result.elementTotals ?? {})
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([symbol, total]) => (
                  <tr key={symbol}>
                    <td className="mono">{symbol}</td>
                    <td className="mono">{total.reactant}</td>
                    <td className="mono">{total.product}</td>
                    <td>
                      {total.reactant === total.product && total.reactant > 0
                        ? "✓ 守恒"
                        : "✗ 不守恒"}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>
        </>
      )}

      <div
        className={`certificate ${certificateStale ? "stale" : "fresh"}`}
        data-testid="certificate"
      >
        <strong>证书 {certificateStale ? "（已撤销）" : ""}</strong>
        <div className="mono small">{result.certificate.certificateId}</div>
        <div className="small dim">
          输入指纹：{result.certificate.inputFingerprint}
          {"　·　签发："}
          {result.certificate.issuedAt}
        </div>
        {certificateStale && (
          <div className="revocation-note" data-testid="revocation-note">
            ⚠ 输入自证书签发后已被修改，旧证书立即失效；请重新求解。
          </div>
        )}
      </div>
    </section>
  );
}
