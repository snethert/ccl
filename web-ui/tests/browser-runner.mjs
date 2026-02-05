import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WEB_UI_ROOT = path.resolve(__dirname, "..");

const MIME_TYPES = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".svg", "image/svg+xml; charset=utf-8"],
]);

function contentTypeFor(filePath) {
  return MIME_TYPES.get(path.extname(filePath)) ?? "application/octet-stream";
}

function toSafePath(rootDir, urlPath) {
  const decoded = decodeURIComponent(urlPath);
  const cleaned = decoded.replace(/\\/g, "/");
  const relative = cleaned.replace(/^\/+/, "");
  const joined = path.join(rootDir, relative);
  const resolved = path.resolve(joined);
  if (!resolved.startsWith(path.resolve(rootDir) + path.sep)) {
    return null;
  }
  return resolved;
}

function startStaticServer(rootDir) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      try {
        const url = new URL(req.url ?? "/", "http://127.0.0.1");
        const filePath = toSafePath(rootDir, url.pathname);
        if (!filePath) {
          res.statusCode = 403;
          res.end("Forbidden");
          return;
        }
        let stat;
        try {
          stat = await fs.stat(filePath);
        } catch {
          res.statusCode = 404;
          res.end("Not found");
          return;
        }
        if (stat.isDirectory()) {
          res.statusCode = 404;
          res.end("Not found");
          return;
        }
        const data = await fs.readFile(filePath);
        res.statusCode = 200;
        res.setHeader("Content-Type", contentTypeFor(filePath));
        res.end(data);
      } catch (err) {
        res.statusCode = 500;
        res.end("Server error");
      }
    });
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const { port } = server.address();
      resolve({
        server,
        baseUrl: `http://127.0.0.1:${port}`,
      });
    });
  });
}

function closeServer(server) {
  return new Promise((resolve) => server.close(resolve));
}

export async function runHeadless(options = {}) {
  let playwright;
  try {
    playwright = await import("playwright");
  } catch (err) {
    return { skipped: true, reason: "Playwright not installed" };
  }

  const timeoutMs = options.timeoutMs ?? 5000;
  const { server, baseUrl } = await startStaticServer(WEB_UI_ROOT);
  let browser;
  try {
    browser = await playwright.chromium.launch({ headless: true });
  } catch (err) {
    const strict = process.env.WEB_UI_STRICT_BROWSER_TESTS === "1";
    if (strict) {
      await closeServer(server);
      throw err;
    }
    await closeServer(server);
    return { skipped: true, reason: `Playwright launch failed: ${err.message}` };
  }
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

  const url = `${baseUrl}/tests/browser/harness.html`;
  await page.goto(url);

  try {
    const result = await resultPromise;
    return result;
  } finally {
    await browser.close();
    await closeServer(server);
  }
}
