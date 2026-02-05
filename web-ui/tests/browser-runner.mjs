import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export async function runHeadless(options = {}) {
  let playwright;
  try {
    playwright = await import("playwright");
  } catch (err) {
    return { skipped: true, reason: "Playwright not installed" };
  }

  const timeoutMs = options.timeoutMs ?? 5000;
  const browser = await playwright.chromium.launch({ headless: true });
  const page = await browser.newPage();

  let resolveResult;
  let rejectResult;
  const resultPromise = new Promise((resolve, reject) => {
    resolveResult = resolve;
    rejectResult = reject;
  });

  const timer = setTimeout(() => {
    rejectResult(new Error("Headless test timed out"));
  }, timeoutMs);

  await page.exposeFunction("__WEB_UI_TEST_DONE__", (result) => {
    clearTimeout(timer);
    resolveResult(result);
  });

  const url = pathToFileURL(path.join(__dirname, "browser", "harness.html")).toString();
  await page.goto(url);

  const result = await resultPromise;
  await browser.close();
  return result;
}
