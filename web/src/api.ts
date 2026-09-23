import type { BalanceResponse, Compound, VerifyResponse } from "./types";
import { toApiCompounds } from "./validation";

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const payload = await response.json();
  if (!response.ok) {
    const message =
      payload?.error?.message ?? `请求失败（HTTP ${response.status}）`;
    const code = payload?.error?.code ?? "REQUEST_FAILED";
    throw new Error(`[${code}] ${message}`);
  }
  return payload as T;
}

export async function solveBalance(compounds: Compound[]): Promise<BalanceResponse> {
  return postJson<BalanceResponse>("/api/balance", {
    compounds: toApiCompounds(compounds),
  });
}

export async function verifyCoefficients(
  compounds: Compound[],
  coefficients: Record<string, string>
): Promise<VerifyResponse> {
  const parsed: Record<string, number> = {};
  for (const compound of compounds) {
    parsed[compound.id] = Number(coefficients[compound.id]);
  }
  return postJson<VerifyResponse>("/api/verify", {
    compounds: toApiCompounds(compounds),
    coefficients: parsed,
  });
}
