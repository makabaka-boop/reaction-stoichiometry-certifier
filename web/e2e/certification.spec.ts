import { expect, test } from "@playwright/test";

/**
 * The single certification journey: enter one reaction exactly once, solve it
 * with the exact backend, and perform the manual coefficient review.
 *
 * Reaction entered:
 *   CH4 + O2  -> CO2 + H2O
 *   C: 1/0, H: 4/0, O: 0/2 ; C:1/O:2 ; H:2/O:1
 * Certified primitive vector: CH4=1, O2=2, CO2=1, H2O=2.
 */

test("one entry → exact solve → manual review, with certificate revocation", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "化学方程式精确配平工作台" })).toBeVisible();

  // ------------------------------------------------------------------
  // 1. Single round of data entry: CH4 + O2 -> CO2 + H2O
  // ------------------------------------------------------------------
  await page.getByTestId("add-compound").click();
  await page.getByTestId("add-compound").click();

  const fillCompound = async (
    row: number,
    id: string,
    role: "REACTANT" | "PRODUCT",
    entries: Array<[string, string]>
  ) => {
    await page.getByTestId(`compound-id-${row}`).fill(id);
    await page.getByTestId(`compound-role-${row}`).selectOption(role);
    for (let i = 1; i < entries.length; i++) {
      await page.getByTestId(`add-element-${row}`).click();
    }
    const symbolInputs = page
      .getByTestId(`compound-row-${row}`)
      .getByLabel(/元素符号/);
    const countInputs = page
      .getByTestId(`compound-row-${row}`)
      .getByLabel(/元素下标/);
    for (let i = 0; i < entries.length; i++) {
      await symbolInputs.nth(i).fill(entries[i][0]);
      await countInputs.nth(i).fill(entries[i][1]);
    }
  };

  await fillCompound(0, "CH4", "REACTANT", [
    ["C", "1"],
    ["H", "4"],
  ]);
  await fillCompound(1, "O2", "REACTANT", [["O", "2"]]);
  await fillCompound(2, "CO2", "PRODUCT", [
    ["C", "1"],
    ["O", "2"],
  ]);
  await fillCompound(3, "H2O", "PRODUCT", [
    ["H", "2"],
    ["O", "1"],
  ]);

  // No validation issues; the solve button is enabled.
  await expect(page.getByTestId("issue-list")).toHaveCount(0);
  await expect(page.getByTestId("solve-button")).toBeEnabled();

  // ------------------------------------------------------------------
  // 2. Solve: unique primitive vector, per-element totals, certificate
  // ------------------------------------------------------------------
  await page.getByTestId("solve-button").click();

  await expect(page.getByTestId("status-banner")).toHaveText("唯一原始配方已认证");
  await expect(page.getByTestId("balanced-equation")).toContainText("CH4");
  await expect(page.getByTestId("balanced-equation")).toContainText("2 O2");
  await expect(page.getByTestId("balanced-equation")).toContainText("CO2");
  await expect(page.getByTestId("balanced-equation")).toContainText("2 H2O");

  // Row-by-row hand verification of the element totals.
  const totals = page.getByTestId("totals-table");
  await expect(totals).toContainText("C");
  await expect(totals.locator("tr", { hasText: "C" })).toContainText("1");
  await expect(totals.locator("tr", { hasText: "H" })).toContainText("4");
  await expect(totals.locator("tr", { hasText: "O" })).toContainText("4");
  await expect(page.getByTestId("certificate")).toContainText(/CERT-[0-9A-F]{12}/);
  await expect(page.getByTestId("revocation-note")).toHaveCount(0);

  // ------------------------------------------------------------------
  // 3. Manual review: certified coefficients are prefilled and verify
  // ------------------------------------------------------------------
  await expect(page.getByTestId("review-coeff-0")).toHaveValue("1");
  await expect(page.getByTestId("review-coeff-1")).toHaveValue("2");
  await expect(page.getByTestId("review-coeff-2")).toHaveValue("1");
  await expect(page.getByTestId("review-coeff-3")).toHaveValue("2");

  await page.getByTestId("verify-button").click();
  await expect(page.getByTestId("verdict")).toContainText("全为正整数：是");
  await expect(page.getByTestId("verdict")).toContainText("逐元素守恒：是");
  await expect(page.getByTestId("verdict")).toContainText("最简整数比（GCD=1）：是");
  for (const symbol of ["C", "H", "O"]) {
    await expect(page.getByTestId(`review-element-${symbol}`)).toContainText("✓ 守恒");
  }

  // Break minimality on purpose: 2,4,2,4 conserves but is not primitive.
  await page.getByTestId("review-coeff-0").fill("2");
  await page.getByTestId("review-coeff-1").fill("4");
  await page.getByTestId("review-coeff-2").fill("2");
  await page.getByTestId("review-coeff-3").fill("4");
  await page.getByTestId("verify-button").click();
  await expect(page.getByTestId("verdict")).toContainText("否（GCD=2）");
  await expect(page.getByTestId("review-reasons")).toContainText("NOT_PRIMITIVE_GCD_2");

  // Break conservation on purpose: element O must be flagged individually.
  await page.getByTestId("review-coeff-1").fill("1");
  await page.getByTestId("verify-button").click();
  await expect(page.getByTestId("review-element-C")).toContainText("✓ 守恒");
  await expect(page.getByTestId("review-element-H")).toContainText("✓ 守恒");
  await expect(page.getByTestId("review-element-O")).toContainText("✗ 不守恒");

  // ------------------------------------------------------------------
  // 4. Any edit to the input revokes the old certificate immediately.
  // ------------------------------------------------------------------
  await page.getByTestId("compound-id-0").fill("CH4X");
  await expect(page.getByTestId("revocation-note")).toBeVisible();
  await expect(page.getByTestId("certificate")).toContainText("已撤销");
});
