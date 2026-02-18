import fs from "node:fs/promises";
import http from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const WEB_UI_ROOT = path.resolve(__dirname, "..");
const REPO_ROOT = path.resolve(WEB_UI_ROOT, "..");
const DOC_ROOT = path.join(REPO_ROOT, "doc");
const SCRIPTS_ROOT = path.join(REPO_ROOT, "scripts");
const BUILD_ROOT = path.join(REPO_ROOT, "build");

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

function resolvePath(rootDir, urlPath) {
  const decoded = decodeURIComponent(urlPath);
  const cleaned = decoded.replace(/\\/g, "/");
  if (cleaned.startsWith("/doc/")) {
    const rel = cleaned.replace(/^\/doc\//, "");
    return toSafePath(DOC_ROOT, rel);
  }
  if (cleaned.startsWith("/scripts/")) {
    const rel = cleaned.replace(/^\/scripts\//, "");
    return toSafePath(SCRIPTS_ROOT, rel);
  }
  if (cleaned.startsWith("/build/")) {
    const rel = cleaned.replace(/^\/build\//, "");
    return toSafePath(BUILD_ROOT, rel);
  }
  return toSafePath(rootDir, cleaned);
}

function startStaticServer(rootDir) {
  return new Promise((resolve, reject) => {
    const server = http.createServer(async (req, res) => {
      try {
        const url = new URL(req.url ?? "/", "http://127.0.0.1");
        const filePath = resolvePath(rootDir, url.pathname);
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
    server.on("error", (err) => {
      const code = err?.code ?? "UNKNOWN";
      if (code === "EACCES" || code === "EPERM") {
        const e = new Error(
          `Headless harness failed to bind the local HTTP server on 127.0.0.1 (${code}). ` +
            "This environment blocks listening on localhost. " +
            "Re-run with permissions or allow local network binds. " +
            `Original error: ${err?.message ?? "unknown"}`
        );
        e.code = code;
        reject(e);
        return;
      }
      if (code === "EADDRINUSE") {
        const e = new Error(
          "Headless harness failed to bind the local HTTP server because the port is in use. " +
            "Close the process using the port and try again. " +
            `Original error: ${err?.message ?? "unknown"}`
        );
        e.code = code;
        reject(e);
        return;
      }
      reject(err);
    });
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

async function fulfillFromDisk(route, rootDir) {
  try {
    const url = new URL(route.request().url());
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      await route.continue();
      return;
    }
    const filePath = resolvePath(rootDir, url.pathname);
    if (!filePath) {
      await route.fulfill({ status: 403, body: "Forbidden" });
      return;
    }
    let stat;
    try {
      stat = await fs.stat(filePath);
    } catch {
      await route.fulfill({ status: 404, body: "Not found" });
      return;
    }
    if (stat.isDirectory()) {
      await route.fulfill({ status: 404, body: "Not found" });
      return;
    }
    const data = await fs.readFile(filePath);
    await route.fulfill({
      status: 200,
      body: data,
      headers: {
        "Content-Type": contentTypeFor(filePath),
      },
    });
  } catch (err) {
    await route.fulfill({ status: 500, body: "Server error" });
  }
}

const PLAYWRIGHT_BROWSER_ORDER = ["chromium", "webkit", "firefox"];

function envFlag(name) {
  return process.env[name] === "1";
}

function splitEnvList(name) {
  const raw = process.env[name];
  if (!raw) return [];
  return raw
    .split(",")
    .map((item) => item.trim().toLowerCase())
    .filter(Boolean);
}

function splitEnvArgs(name) {
  const raw = process.env[name];
  if (!raw) return [];
  return raw
    .split(/\s+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function resolveHeadlessMode() {
  if (envFlag("WEB_UI_BROWSER_HEADED")) return false;
  if (process.env.WEB_UI_BROWSER_HEADLESS === "0") return false;
  return true;
}

function resolveBrowserOrder() {
  const requested = splitEnvList("WEB_UI_BROWSER_ORDER");
  const legacy = splitEnvList("WEB_UI_BROWSER");
  const requestedOrder = requested.length > 0 ? requested : legacy;
  if (requestedOrder.length === 0) {
    return [...PLAYWRIGHT_BROWSER_ORDER];
  }
  const order = [];
  for (const name of requestedOrder) {
    if (!PLAYWRIGHT_BROWSER_ORDER.includes(name)) continue;
    if (order.includes(name)) continue;
    order.push(name);
  }
  for (const name of PLAYWRIGHT_BROWSER_ORDER) {
    if (!order.includes(name)) {
      order.push(name);
    }
  }
  return order;
}

function allowLaunchRetries() {
  return process.env.WEB_UI_BROWSER_RETRY_LAUNCHES === "1";
}

function withNoSandboxArgs(args) {
  const merged = [...args];
  if (!merged.includes("--no-sandbox")) {
    merged.push("--no-sandbox");
  }
  if (!merged.includes("--disable-setuid-sandbox")) {
    merged.push("--disable-setuid-sandbox");
  }
  return merged;
}

function attemptName(browserName, { channel, executablePath, noSandbox = false } = {}) {
  const traits = [];
  if (channel) traits.push(`channel=${channel}`);
  if (executablePath) traits.push(`executablePath=${executablePath}`);
  if (noSandbox) traits.push("no-sandbox");
  if (traits.length === 0) return browserName;
  return `${browserName} (${traits.join(", ")})`;
}

function buildPlaywrightLaunchAttempts(playwright) {
  const headless = resolveHeadlessMode();
  const browserOrder = resolveBrowserOrder();
  const args = splitEnvArgs("WEB_UI_BROWSER_ARGS");
  const disableSandbox = envFlag("WEB_UI_BROWSER_DISABLE_SANDBOX");
  const channel = (process.env.WEB_UI_BROWSER_CHANNEL ?? "").trim();
  const executablePath = (process.env.WEB_UI_BROWSER_EXECUTABLE_PATH ?? "").trim();
  const attempts = [];

  for (const browserName of browserOrder) {
    const type = playwright[browserName];
    if (!type) continue;
    const baseOptions = { headless };

    if (browserName === "chromium") {
      if (channel) {
        baseOptions.channel = channel;
      }
      if (executablePath) {
        baseOptions.executablePath = executablePath;
      }
      if (args.length > 0) {
        baseOptions.args = [...args];
      }

      const argsHaveNoSandbox = (baseOptions.args ?? []).includes("--no-sandbox");
      if (!disableSandbox) {
        attempts.push({
          name: attemptName("chromium", baseOptions),
          type,
          options: baseOptions,
        });
      }
      if (disableSandbox || !argsHaveNoSandbox) {
        const sandboxOptions = {
          ...baseOptions,
          args: withNoSandboxArgs(baseOptions.args ?? []),
        };
        attempts.push({
          name: attemptName("chromium", { ...sandboxOptions, noSandbox: true }),
          type,
          options: sandboxOptions,
        });
      }
      continue;
    }

    attempts.push({
      name: attemptName(browserName),
      type,
      options: baseOptions,
    });
  }

  return attempts;
}

function buildLaunchSuggestions(errors) {
  const joined = errors.join("\n");
  const suggestions = [];
  if (/Executable doesn't exist|executable doesn't exist|Please run:\s*npx playwright install/i.test(joined)) {
    suggestions.push("Install Playwright browsers: npx playwright install chromium firefox webkit");
  }
  if (/EPERM|EACCES|Operation not permitted|Mach port|sandbox/i.test(joined)) {
    suggestions.push(
      "If launch permissions are restricted, retry with WEB_UI_BROWSER_DISABLE_SANDBOX=1."
    );
  }
  if (/No usable sandbox|setuid sandbox|namespace sandbox/i.test(joined)) {
    suggestions.push("Set WEB_UI_BROWSER_DISABLE_SANDBOX=1 for restricted Linux/macOS environments.");
  }
  if (suggestions.length === 0) {
    return "";
  }
  return `\nSuggestions:\n${suggestions.map((item) => `- ${item}`).join("\n")}`;
}

async function launchPlaywrightBrowser(playwright) {
  const attempts = buildPlaywrightLaunchAttempts(playwright);
  const effectiveAttempts = allowLaunchRetries() ? attempts : attempts.slice(0, 1);
  const errors = [];
  for (const attempt of effectiveAttempts) {
    if (!attempt.type) continue;
    try {
      const browser = await attempt.type.launch(attempt.options);
      return { browser, name: attempt.name };
    } catch (err) {
      errors.push(`${attempt.name}: ${err?.message ?? err}`);
    }
  }
  if (!allowLaunchRetries() && attempts.length > 1) {
    errors.push(
      "Additional launch attempts were skipped. Set WEB_UI_BROWSER_RETRY_LAUNCHES=1 to re-enable fallback launch attempts."
    );
  }
  const suggestions = buildLaunchSuggestions(errors);
  const e = new Error(`Playwright launch failed:\n${errors.join("\n")}${suggestions}`);
  e.details = errors;
  throw e;
}

export async function runHeadless(options = {}) {
  let playwright;
  try {
    playwright = await import("playwright");
  } catch (err) {
    return { skipped: true, reason: "Playwright not installed" };
  }

  const timeoutMs = options.timeoutMs ?? 5000;
  const debug = options.debug === true || process.env.WEB_UI_BROWSER_DEBUG === "1";
  const kernelEnabled = options.kernelEnabled !== false;
  let server;
  let baseUrl;
  let useRouteServer = false;
  try {
    ({ server, baseUrl } = await startStaticServer(WEB_UI_ROOT));
  } catch (err) {
    const strict = process.env.WEB_UI_STRICT_BROWSER_TESTS === "1";
    if (strict) {
      throw err;
    }
    const code = err?.code ?? "";
    if (code === "EACCES" || code === "EPERM") {
      useRouteServer = true;
      baseUrl = "http://web-ui.local";
    } else {
      return { skipped: true, reason: err?.message ?? "Failed to start local HTTP server" };
    }
  }
  let browser;
  let browserName = "chromium";
  try {
    const launched = await launchPlaywrightBrowser(playwright);
    browser = launched.browser;
    browserName = launched.name;
  } catch (err) {
    const strict = process.env.WEB_UI_STRICT_BROWSER_TESTS === "1";
    if (strict) {
      if (server) await closeServer(server);
      throw err;
    }
    if (server) await closeServer(server);
    return { skipped: true, reason: err?.message ?? "Playwright launch failed" };
  }
  const page = await browser.newPage();
  const debugLogs = [];
  if (debug) {
    page.on("console", (msg) => {
      debugLogs.push(`console.${msg.type()}: ${msg.text()}`);
    });
    page.on("pageerror", (err) => {
      debugLogs.push(`pageerror: ${err?.message ?? String(err)}`);
    });
    page.on("response", (res) => {
      if (res.status() >= 400) {
        debugLogs.push(`http.${res.status()}: ${res.url()}`);
      }
    });
    page.on("requestfailed", (req) => {
      debugLogs.push(`requestfailed: ${req.url()} (${req.failure()?.errorText ?? "unknown"})`);
    });
  }
  if (useRouteServer) {
    await page.route("**/*", (route) => fulfillFromDisk(route, WEB_UI_ROOT));
  }

  let resolveResult;
  let rejectResult;
  const resultPromise = new Promise((resolve, reject) => {
    resolveResult = resolve;
    rejectResult = reject;
  });

  const timer = setTimeout(() => {
    const suffix = debugLogs.length > 0
      ? `\nBrowser diagnostics:\n${debugLogs.join("\n")}`
      : "";
    rejectResult(new Error(`Headless test timed out${suffix}`));
  }, timeoutMs);

  await page.exposeFunction("__WEB_UI_TEST_DONE__", (result) => {
    clearTimeout(timer);
    resolveResult(result);
  });

  const params = new URLSearchParams();
  if (!kernelEnabled) {
    params.set("kernel", "off");
  }
  const query = params.toString();
  const url = `${baseUrl}/tests/browser/harness.html${query ? `?${query}` : ""}`;
  await page.goto(url);

  try {
    const result = await resultPromise;
    result.browserName = browserName;
    if (debug && debugLogs.length > 0) {
      result.debugLogs = debugLogs;
    }
    return result;
  } finally {
    await browser.close();
    if (server) await closeServer(server);
  }
}
