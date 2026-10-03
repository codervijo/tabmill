import { expect, test } from "./fixtures";

test("side panel renders the branded shell", async ({ page, extensionId }) => {
  expect(extensionId).not.toBe("");
  await page.goto(`chrome-extension://${extensionId}/sidepanel.html`);
  await expect(page.locator("h1")).not.toBeEmpty();
  await expect(page.locator("footer")).toContainText("Built by Lamill");
  await expect(page.getByTestId("privacy")).not.toBeEmpty();
  await expect(page.locator("a.lm-cta")).toHaveAttribute("href", /utm_campaign=/);
});
