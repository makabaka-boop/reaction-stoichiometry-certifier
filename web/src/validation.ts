import { ELEMENT_SYMBOLS, MAX_COMPOUNDS, MAX_ELEMENTS, MIN_COMPOUNDS } from "./elements";
import type { Compound, Role } from "./types";

export interface ValidationIssue {
  message: string;
}

const ASCII_ID = /^[\x20-\x7E]+$/;
const POSITIVE_INT = /^[1-9][0-9]*$/;

/** Client-side mirror of backend/app/validation.py plus a duplicate-element
 *  guard for the row editor. The server remains authoritative; these checks
 *  give instant feedback and keep malformed requests from leaving the page.
 *  Returns [] when the document is ready to certify. */
export function validateCompounds(compounds: Compound[]): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  if (compounds.length < MIN_COMPOUNDS || compounds.length > MAX_COMPOUNDS) {
    issues.push({
      message: `化合物数量必须在 ${MIN_COMPOUNDS} 至 ${MAX_COMPOUNDS} 之间（当前 ${compounds.length}）`,
    });
    return issues;
  }

  const seen = new Set<string>();
  const elements = new Set<string>();

  compounds.forEach((compound, row) => {
    const where = `第 ${row + 1} 行`;
    const id = compound.id.trim();

    if (!ASCII_ID.test(compound.id)) {
      issues.push({ message: `${where}：ID 必须为非空 ASCII 字符` });
    } else if (seen.has(id)) {
      issues.push({ message: `${where}：ID「${id}」重复` });
    } else {
      seen.add(id);
    }

    if (compound.role !== "REACTANT" && (compound.role as Role) !== "PRODUCT") {
      issues.push({ message: `${where}：角色必须是 REACTANT 或 PRODUCT` });
    }

    if (compound.composition.length === 0) {
      issues.push({ message: `${where}：组成不能为空` });
    }
    const rowSymbols = new Set<string>();
    for (const { symbol, count } of compound.composition) {
      if (symbol === "" || count.trim() === "") {
        issues.push({ message: `${where}：存在未填写完整的元素项` });
        continue;
      }
      if (!ELEMENT_SYMBOLS.has(symbol)) {
        issues.push({ message: `${where}：非法元素符号「${symbol}」` });
      } else {
        elements.add(symbol);
        if (rowSymbols.has(symbol)) {
          issues.push({ message: `${where}：元素 ${symbol} 重复` });
        }
        rowSymbols.add(symbol);
      }
      if (!POSITIVE_INT.test(count.trim())) {
        issues.push({
          message: `${where}：元素 ${symbol} 的下标必须是正整数（当前「${count}」）`,
        });
      }
    }
  });

  if (elements.size > MAX_ELEMENTS) {
    issues.push({ message: `元素总数不得超过 ${MAX_ELEMENTS} 种（当前 ${elements.size}）` });
  }
  return issues;
}

export function toApiCompounds(compounds: Compound[]) {
  return compounds.map((compound) => ({
    id: compound.id,
    role: compound.role,
    composition: Object.fromEntries(
      compound.composition.map(({ symbol, count }) => [symbol, Number(count)])
    ),
  }));
}
