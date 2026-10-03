import { expect, test } from "./fixtures";

test("side panel offers the audit action", async ({ page, extensionId }) => {
  await page.goto(`chrome-extension://${extensionId}/sidepanel.html`);
  await expect(page.getByRole("button", { name: "Audit this page" })).toBeVisible();
});
