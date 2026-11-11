import { chromium } from "playwright-core";
import { fileURLToPath } from "node:url";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const out = fileURLToPath(new URL("../artifacts/", import.meta.url));
const browser = await chromium.launch({
  executablePath: edge,
  headless: true,
  args: ["--disable-gpu", "--no-sandbox", "--enable-logging=stderr", "--v=1"],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
page.on("console", (message) => console.log(`[console:${message.type()}]`, message.text()));
page.on("pageerror", (error) => console.log("[pageerror]", error.message));
page.on("requestfailed", (request) => console.log("[requestfailed]", request.url(), request.failure()?.errorText));
page.on("response", (response) => {
  if (response.status() >= 400) console.log("[http]", response.status(), response.url());
});

await page.goto("http://127.0.0.1:8787", { waitUntil: "networkidle" });
console.log("db badge:", await page.locator("#dbBadge").innerText());
console.log("backend:", await page.locator("#backendBadge").innerText());
await page.click("#loadSamples");
console.log("textarea length:", await page.locator("#docInput").inputValue().then((v) => v.length));
console.log("chunk count:", await page.locator("#chunkCount").innerText());
console.log("import disabled:", await page.locator("#importBtn").isDisabled());
await page.click("#importBtn");
for (let i = 0; i < 12; i += 1) {
  await page.waitForTimeout(5000);
  console.log(`t+${(i + 1) * 5}s status=`, await page.locator("#importStatusText").innerText());
  console.log(`t+${(i + 1) * 5}s backend=`, await page.locator("#backendBadge").innerText());
}
await page.screenshot({ path: `${out}/debug.png`, fullPage: true });
await browser.close();
