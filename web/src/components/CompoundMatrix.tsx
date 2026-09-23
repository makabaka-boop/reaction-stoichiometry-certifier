import { ELEMENT_SYMBOLS } from "../elements";
import type { Compound, Role } from "../types";

interface Props {
  compounds: Compound[];
  onChange: (next: Compound[]) => void;
}

const newCompound = (): Compound => ({
  id: "",
  role: "REACTANT",
  composition: [{ symbol: "", count: "" }],
});

export function CompoundMatrix({ compounds, onChange }: Props) {
  const patch = (index: number, next: Partial<Compound>) => {
    onChange(compounds.map((row, i) => (i === index ? { ...row, ...next } : row)));
  };

  const patchEntry = (
    compoundIndex: number,
    entryIndex: number,
    next: Partial<{ symbol: string; count: string }>
  ) => {
    const composition = compounds[compoundIndex].composition.map((entry, i) =>
      i === entryIndex ? { ...entry, ...next } : entry
    );
    patch(compoundIndex, { composition });
  };

  const addElement = (index: number) => {
    patch(index, {
      composition: [...compounds[index].composition, { symbol: "", count: "" }],
    });
  };

  const removeElement = (index: number, entryIndex: number) => {
    patch(index, {
      composition: compounds[index].composition.filter((_, i) => i !== entryIndex),
    });
  };

  const addCompound = () => onChange([...compounds, newCompound()]);

  const removeCompound = (index: number) =>
    onChange(compounds.filter((_, i) => i !== index));

  return (
    <section className="panel" data-testid="compound-matrix">
      <h2>① 化合物矩阵</h2>
      <p className="hint">
        每行一个化合物：ASCII ID、角色（REACTANT 为正 / PRODUCT 为负）、元素符号→正整数下标。
        未知字段、重复 ID、非法元素符号或空组成会导致整份请求被拒绝。
      </p>

      <div className="compound-list">
        {compounds.map((compound, index) => (
          <div
            className={`compound-row role-${compound.role.toLowerCase()}`}
            key={index}
            data-testid={`compound-row-${index}`}
          >
            <div className="compound-head">
              <span className="row-index">#{index + 1}</span>
              <input
                aria-label={`化合物 ${index + 1} ID`}
                data-testid={`compound-id-${index}`}
                className="id-input"
                value={compound.id}
                placeholder="ASCII ID，如 H2O"
                onChange={(event) => patch(index, { id: event.target.value })}
              />
              <select
                aria-label={`化合物 ${index + 1} 角色`}
                data-testid={`compound-role-${index}`}
                value={compound.role}
                onChange={(event) =>
                  patch(index, { role: event.target.value as Role })
                }
              >
                <option value="REACTANT">REACTANT（反应物 +）</option>
                <option value="PRODUCT">PRODUCT（产物 −）</option>
              </select>
              <button
                type="button"
                className="danger small"
                data-testid={`compound-remove-${index}`}
                onClick={() => removeCompound(index)}
                disabled={compounds.length <= 2}
                title="至少保留两个化合物"
              >
                删除
              </button>
            </div>

            <div className="composition-grid">
              {compound.composition.map((entry, entryIndex) => (
                <div className="composition-entry" key={entryIndex}>
                  <input
                    aria-label={`化合物 ${index + 1} 元素符号`}
                    className={`symbol-input ${
                      entry.symbol !== "" && !ELEMENT_SYMBOLS.has(entry.symbol)
                        ? "invalid"
                        : ""
                    }`}
                    value={entry.symbol}
                    placeholder="元素"
                    list="element-list"
                    onChange={(event) =>
                      patchEntry(index, entryIndex, { symbol: event.target.value })
                    }
                  />
                  <span className="colon">∶</span>
                  <input
                    aria-label={`化合物 ${index + 1} 元素下标`}
                    className="count-input"
                    inputMode="numeric"
                    value={entry.count}
                    placeholder="正整数"
                    onChange={(event) =>
                      patchEntry(index, entryIndex, { count: event.target.value })
                    }
                  />
                  <button
                    type="button"
                    className="ghost small"
                    onClick={() => removeElement(index, entryIndex)}
                    title="删除该元素"
                  >
                    ×
                  </button>
                </div>
              ))}
              <button
                type="button"
                className="ghost small add-element"
                data-testid={`add-element-${index}`}
                onClick={() => addElement(index)}
              >
                + 添加元素
              </button>
            </div>
          </div>
        ))}
      </div>

      <datalist id="element-list">
        {[...ELEMENT_SYMBOLS].map((symbol) => (
          <option key={symbol} value={symbol} />
        ))}
      </datalist>

      <button
        type="button"
        className="secondary"
        data-testid="add-compound"
        onClick={addCompound}
        disabled={compounds.length >= 12}
      >
        + 添加化合物
      </button>
    </section>
  );
}
