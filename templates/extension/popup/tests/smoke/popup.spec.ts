import { expect, test } from "./fixtures";

test("popup renders the branded shell", async ({ page, extensionId }) => {
  expect(extensionId).not.toBe("");
  await page.goto(`chrome-extension://${extensionId}/popup.html`);
  await expect(page.locator("h1")).not.toBeEmpty();
  await expect(page.locator("footer")).toContainText("Built by Lamill");
  await expect(page.getByTestId("privacy")).not.toBeEmpty();
  const cta = page.locator("a.lm-cta");
  await expect(cta).toHaveAttribute("href", /utm_campaign=/);
});
