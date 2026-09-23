import { useState } from "react";
import type { Compound, VerifyResponse } from "../types";
import { verifyCoefficients } from "../api";

interface Props {
  compounds: Compound[];
  /** Certified coefficients, pre-filled after a BALANCED solve. The parent
   *  remounts this panel (via key) on every solve, so the initial state is
   *  always the latest certified primitive vector. */
  suggested: Record<string, number>;
  /** Bumped whenever the editor changes; disables stale verdicts. */
  editEpoch: number;
}

const INT = /^-?[0-9]+$/;

export function ReviewPanel({ compounds, suggested, editEpoch }: Props) {
  const [coefficients, setCoefficients] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(suggested).map(([id, value]) => [id, String(value)]))
  );
  const [verification, setVerification] = useState<VerifyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [checkedEpoch, setCheckedEpoch] = useState<number | null>(null);

  const effective = (id: string) => coefficients[id] ?? "";

  const stale = checkedEpoch !== null && checkedEpoch !== editEpoch;

  const update = (id: string, value: string) => {
    setCoefficients((prev) => ({ ...prev, [id]: value }));
    setVerification(null);
  };

  const runVerify = async () => {
    setError(null);
    const payload = Object.fromEntries(compounds.map((c) => [c.id, effective(c.id)]));
    if (compounds.some((c) => !INT.test(payload[c.id].trim()))) {
      setError("每个系数都必须是整数（可以尝试 0 或负数观察逐元素不守恒）");
      return;
    }
    try {
      const response = await verifyCoefficients(compounds, payload);
      setVerification(response);
      setCheckedEpoch(editEpoch);
    } catch (err) {
      setError(err instanceof Error ? err.message : "复核请求失败");
    }
  };

  return (
    <section className="panel" data-testid="review-panel">
      <h2>④ 人工系数复核</h2>
      <p className="hint">
        填入待复核的整数系数（默认带入刚认证的原始系数）。系统逐元素核对两侧原子总数，
        并检查是否全为正整数、整体最大公约数是否为 1（最简）。
      </p>

      <div className="review-grid">
        {compounds.map((compound, index) => (
          <label className="review-entry" key={`${compound.id}-${index}`}>
            <span className={`role-tag ${compound.role.toLowerCase()}`}>
              {compound.role === "REACTANT" ? "+" : "−"}
            </span>
            <span className="mono compound-name">{compound.id || `(第${index + 1}行)`}</span>
            <input
              aria-label={`${compound.id} 复核系数`}
              data-testid={`review-coeff-${index}`}
              className="coeff-input"
              inputMode="numeric"
              value={effective(compound.id)}
              disabled={!compound.id}
              onChange={(event) => update(compound.id, event.target.value)}
            />
          </label>
        ))}
      </div>

      <button type="button" className="primary" data-testid="verify-button" onClick={runVerify}>
        复核这些系数
      </button>
      {error && (
        <div className="error-text" data-testid="review-error">
          {error}
        </div>
      )}

      {verification && (
        <div className={`verdict ${stale ? "stale" : ""}`} data-testid="verdict">
          {stale && (
            <div className="revocation-note" data-testid="verdict-stale">
              ⚠ 输入已修改，以下复核结论基于旧输入，已自动失效。
            </div>
          )}
          <div className="verdict-flags">
            <span className={verification.allPositive ? "flag ok" : "flag bad"}>
              全为正整数：{verification.allPositive ? "是" : "否"}
            </span>
            <span className={verification.balanced ? "flag ok" : "flag bad"}>
              逐元素守恒：{verification.balanced ? "是" : "否"}
            </span>
            <span className={verification.primitive ? "flag ok" : "flag warn"}>
              最简整数比（GCD=1）：{verification.primitive ? "是" : `否（GCD=${verification.gcd}）`}
            </span>
          </div>

          <table className="totals-table" data-testid="review-table">
            <thead>
              <tr>
                <th>元素</th>
                <th>反应物侧</th>
                <th>产物侧</th>
                <th>判定</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(verification.elementChecks)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([symbol, check]) => (
                  <tr key={symbol} className={check.balanced ? "" : "row-bad"}>
                    <td className="mono">{symbol}</td>
                    <td className="mono">{check.reactant}</td>
                    <td className="mono">{check.product}</td>
                    <td data-testid={`review-element-${symbol}`}>
                      {check.balanced ? "✓ 守恒" : `✗ 不守恒（差 ${check.reactant - check.product}）`}
                    </td>
                  </tr>
                ))}
            </tbody>
          </table>

          {verification.reasons.length > 0 && (
            <ul className="reason-list" data-testid="review-reasons">
              {verification.reasons.map((reason) => (
                <li key={reason} className="mono small">
                  {reason}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  );
}
