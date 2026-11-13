import { chromium } from "playwright-core";
import { mkdir } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const base = process.env.BASE_URL || "http://127.0.0.1:8787";
const out = fileURLToPath(new URL("../artifacts/", import.meta.url));
await mkdir(out, { recursive: true });

const browser = await chromium.launch({
  executablePath: edge,
  headless: true,
  args: ["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"],
});
const page = await browser.newPage({ viewport: { width: 1440, height: 1200 }, deviceScaleFactor: 1 });
const messages = [];
page.on("console", (message) => messages.push(`[${message.type()}] ${message.text()}`));
page.on("pageerror", (error) => messages.push(`[pageerror] ${error.message}`));

await page.goto(base, { waitUntil: "networkidle" });
await page.screenshot({ path: `${out}/home.png`, fullPage: true });
console.log("title:", await page.title());
console.log("backend:", await page.locator("#backendBadge").innerText());
console.log("db:", await page.locator("#dbBadge").innerText());

await page.click("#loadSamples");
await page.click("#importBtn");
await page.waitForFunction(
  () => {
    const text = document.querySelector("#importStatusText")?.textContent || "";
    return text.includes("seekdb") || text.includes("失败") || text.includes("已写入") || text.includes("未连接");
  },
  null,
  { timeout: 240_000 },
);
console.log("status:", await page.locator("#importStatusText").innerText());
console.log("backend after:", await page.locator("#backendBadge").innerText());
console.log("chunks:", await page.locator("#chunkCount").innerText());
console.log("embed:", await page.locator("#metricEmbed").innerText());
await page.screenshot({ path: `${out}/import.png`, fullPage: true });

console.log("console:");
for (const message of messages) console.log(" ", message);
await browser.close();
