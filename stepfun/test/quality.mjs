import { chromium } from "playwright-core";
import { fileURLToPath } from "node:url";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const out = fileURLToPath(new URL("../artifacts/", import.meta.url));
const browser = await chromium.launch({
  executablePath: edge,
  headless: true,
  args: ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 } });
page.on("console", (message) => {
  if (message.type() === "error") console.log("[console:error]", message.text().slice(0, 300));
});
page.on("pageerror", (error) => console.log("[pageerror]", error.message));

await page.goto("http://127.0.0.1:8787", { waitUntil: "networkidle" });
await page.click("#qualityBtn");
await page.waitForFunction(
  () => {
    const output = document.querySelector("#qualityOutput");
    return output && !output.hidden && /Recall@5|失败/.test(output.textContent || "");
  },
  null,
  { timeout: 600_000 },
);
console.log(await page.locator("#qualityOutput").innerText());
await page.screenshot({ path: `${out}/quality.png`, fullPage: true });
await browser.close();
