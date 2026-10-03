import { type BrowserContext, chromium, test as base } from "@playwright/test";
import path from "node:path";

const extensionPath = path.resolve(import.meta.dirname, "../../.output/chrome-mv3");

export const test = base.extend<{ context: BrowserContext; extensionId: string }>({
  // Playwright fixtures require an object-destructuring first argument, even when empty.
  context: async ({}, use) => {
    const context = await chromium.launchPersistentContext("", {
      channel: "chromium",
      args: [`--disable-extensions-except=${extensionPath}`, `--load-extension=${extensionPath}`],
    });
    await use(context);
    await context.close();
  },
  extensionId: async ({ context }, use) => {
    // Popup-only extensions have no service worker; read the ID from chrome://extensions.
    const page = await context.newPage();
    await page.goto("chrome://extensions");
    const id = await page.evaluate(async () => {
      const mgr = document.querySelector("extensions-manager");
      const item = mgr?.shadowRoot
        ?.querySelector("extensions-item-list")
        ?.shadowRoot?.querySelector("extensions-item");
      return item?.id ?? "";
    });
    await page.close();
    await use(id);
  },
});
export const expect = test.expect;
