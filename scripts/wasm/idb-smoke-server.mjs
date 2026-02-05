import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.env.CCL_HTTP_ROOT || path.join(process.cwd()));
const port = Number(process.env.PORT || 5173);

const mime = new Map([
  [".html", "text/html; charset=utf-8"],
  [".js", "text/javascript; charset=utf-8"],
  [".mjs", "text/javascript; charset=utf-8"],
  [".css", "text/css; charset=utf-8"],
  [".json", "application/json; charset=utf-8"],
  [".wasm", "application/wasm"],
]);

function safePath(urlPath) {
  const decoded = decodeURIComponent(urlPath.split("?")[0]);
  const rel = decoded.replace(/^\/+/g, "");
  const full = path.resolve(root, rel);
  if (!full.startsWith(root)) return null;
  return full;
}

const server = http.createServer((req, res) => {
  const filePath = safePath(req.url || "/");
  if (!filePath) {
    res.writeHead(400);
    res.end("bad request");
    return;
  }

  let stat;
  try {
    stat = fs.statSync(filePath);
  } catch {
    res.writeHead(404);
    res.end("not found");
    return;
  }

  let finalPath = filePath;
  if (stat.isDirectory()) {
    finalPath = path.join(filePath, "index.html");
  }

  try {
    const data = fs.readFileSync(finalPath);
    const ext = path.extname(finalPath);
    const contentType = mime.get(ext) || "application/octet-stream";
    res.writeHead(200, {
      "Content-Type": contentType,
      "Access-Control-Allow-Origin": "*",
      "Cache-Control": "no-store",
    });
    res.end(data);
  } catch {
    res.writeHead(404);
    res.end("not found");
  }
});

server.listen(port, "127.0.0.1", () => {
  // eslint-disable-next-line no-console
  console.log(`idb-smoke server: http://127.0.0.1:${port}`);
  // eslint-disable-next-line no-console
  console.log(`root: ${root}`);
});
