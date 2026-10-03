import { expect, test } from "./fixtures";

// `chrome` exists inside the extension page that page.evaluate runs in; this test file is
// compiled for Node, so declare just the slice it uses.
declare const chrome: {
  storage: {
    session: {
      set(items: Record<string, unknown>): Promise<void>;
      get(key: string): Promise<Record<string, unknown>>;
    };
  };
};

test("print page renders a handed-off article, sanitized", async ({ context, page, extensionId }) => {
  // Don't open the real print dialog in tests.
  await context.addInitScript(() => {
    window.print = () => {
      document.body.dataset.printed = "yes";
    };
  });
  await page.goto(`chrome-extension://${extensionId}/popup.html`);
  await page.evaluate(async () => {
    await chrome.storage.session.set({
      "print:test": {
        title: "Fixture Article",
        url: "https://fixture.test/post",
        html:
          '<p id="ok">Hello <a href="/rel">link</a></p>' +
          '<img src="x" onerror="document.body.dataset.pwned=1">' +
          "<script>document.body.dataset.pwned=1</script>" +
          '<a href="javascript:alert(1)">bad</a>',
        byline: null,
        siteName: "Fixture",
        lang: "en",
        fallback: false,
      },
    });
  });
  await page.goto(`chrome-extension://${extensionId}/print.html#print:test`);
  await expect(page.locator("#doc h1")).toHaveText("Fixture Article");
  await expect(page).toHaveTitle("Fixture Article");
  await expect(page.locator("#doc p", { hasText: "Hello" })).toBeVisible();
  await expect(page.locator('#doc a[href="https://fixture.test/rel"]')).toHaveCount(1);
  expect(await page.locator("#doc script").count()).toBe(0);
  expect(await page.locator("#doc [onerror]").count()).toBe(0);
  expect(await page.locator('#doc a[href^="javascript"]').count()).toBe(0);
  await expect(page.locator("body")).toHaveAttribute("data-printed", "yes", { timeout: 5000 });
  expect(await page.evaluate(() => document.body.dataset.pwned)).toBeUndefined();
  // Handoff is consumed on read.
  const left = await page.evaluate(() => chrome.storage.session.get("print:test"));
  expect(left).toEqual({});
});

test("popup shows save actions", async ({ page, extensionId }) => {
  await page.goto(`chrome-extension://${extensionId}/popup.html`);
  await expect(page.getByRole("button", { name: "Save as Markdown" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Save as PDF" })).toBeVisible();
});
