import { expect, test } from "./fixtures";

test("extension loads with a toolbar action and background", async ({ context, extensionId }) => {
  expect(extensionId).not.toBe("");
  let [sw] = context.serviceWorkers();
  if (!sw) sw = await context.waitForEvent("serviceworker");
  expect(sw.url()).toContain(`chrome-extension://${extensionId}/background.js`);
});

test("overlay panel renders the branded shell", async ({ page, extensionId }) => {
  await page.goto(`chrome-extension://${extensionId}/overlay-preview.html`);
  await expect(page.locator("footer")).toContainText("Built by Lamill");
  await expect(page.locator("a.lm-cta")).toHaveAttribute("href", /utm_campaign=/);
});
