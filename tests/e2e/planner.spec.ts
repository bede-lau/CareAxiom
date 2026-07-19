import { expect, test } from "@playwright/test";

test("opens the planner with the embedded Facility Trust Desk", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Planner", exact: true })).toBeVisible();
  await expect(page.getByText("Facility Trust Desk", { exact: true })).toBeVisible();
});

test("keeps NFHS district context on a separate context axis", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByText("Separate context axis", { exact: true })).toBeVisible();
  await expect(page.getByText("NFHS district context", { exact: true })).toBeVisible();
});

test("shows geography conflicts without silently accepting district assignment", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Facility record").selectOption({ label: "Lifecare Hospital" });
  await expect(page.getByRole("alert").getByText("Location conflict")).toBeVisible();
  await expect(page.getByText(/City: Siwan/)).toBeVisible();
  await expect(page.getByText(/excluded from confident planning results/i)).toBeVisible();
});

test("saves and reopens a scenario", async ({ page }) => {
  const scenarioName = "E2E saved scenario";
  await page.goto("/");
  await page.getByRole("button", { name: "Save scenario" }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Name").fill(scenarioName);
  await dialog.getByRole("button", { name: "Save scenario" }).click();
  await expect(dialog).toBeHidden();
  const openNavigation = page.getByRole("button", { name: "Open navigation" });
  if (await openNavigation.isVisible()) {
    await openNavigation.click();
  }
  await page.getByRole("button", { name: "Scenarios" }).click();
  await expect(page.getByRole("heading", { name: scenarioName, exact: true })).toBeVisible();
});

test("does not expose Referral Copilot in default navigation", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("navigation").getByText("Referral Copilot")).toHaveCount(0);
});

test("keeps Tavily verification reviewer-triggered and cached by default", async ({ page }) => {
  await page.goto("/");
  const openNavigation = page.getByRole("button", { name: "Open navigation" });
  if (await openNavigation.isVisible()) {
    await openNavigation.click();
  }
  await page.getByRole("button", { name: "Verification Queue", exact: true }).click();
  await page.getByRole("button", { name: "Check external sources" }).click();
  await expect(page.getByText("Cached mode made no external request.")).toBeVisible();
});
