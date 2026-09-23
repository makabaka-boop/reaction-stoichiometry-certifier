export type Role = "REACTANT" | "PRODUCT";

/** One element/count pair as edited in a compound row. Ordered so that two
 *  blank "add element" rows can coexist before the user types a symbol. */
export interface CompositionEntry {
  symbol: string;
  count: string;
}

/** A compound row as edited in the matrix. Counts are kept as the raw
 *  positive-integer strings while typing; they are parsed on solve. */
export interface Compound {
  id: string;
  role: Role;
  composition: CompositionEntry[];
}

export interface ElementTotal {
  reactant: number;
  product: number;
}

export interface CoefficientEntry {
  id: string;
  coefficient: number;
}

export interface Certificate {
  certificateId: string;
  issuedAt: string;
  inputFingerprint: string;
  status: BalanceStatus;
  reason: string;
}

export type BalanceStatus =
  | "BALANCED"
  | "NO_BALANCE"
  | "UNDERDETERMINED"
  | "NO_POSITIVE_BALANCE";

export interface BalanceResponse {
  status: BalanceStatus;
  nullity: number;
  reason?: string;
  coefficients?: CoefficientEntry[];
  elementTotals?: Record<string, ElementTotal>;
  certificate: Certificate;
}

export interface ElementCheck {
  reactant: number;
  product: number;
  balanced: boolean;
}

export interface VerifyResponse {
  balanced: boolean;
  primitive: boolean;
  gcd: number;
  allPositive: boolean;
  reasons: string[];
  elementChecks: Record<string, ElementCheck>;
  elementTotals: Record<string, ElementTotal>;
}

export interface ApiError {
  error: { code: string; message: string };
}
