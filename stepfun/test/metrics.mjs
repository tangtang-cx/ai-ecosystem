import { chromium } from "playwright-core";

const edge = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const browser = await chromium.launch({
  executablePath: edge,
  headless: true,
  args: ["--disable-gpu", "--no-sandbox"],
});
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
await page.goto("http://127.0.0.1:8787", { waitUntil: "networkidle" });
await page.click("#loadSamples");
await page.click("#importBtn");
await page.waitForFunction(
  () => /seekdb 未连接|已写入/.test(document.querySelector("#importStatusText")?.textContent || ""),
  null,
  { timeout: 120_000 },
);
for (const id of ["metricLoad", "metricEmbed", "metricEmbedRate", "metricQueryEmbed", "backendBadge", "metricModel"]) {
  console.log(id, "=", await page.locator(`#${id}`).innerText());
}
await browser.close();
