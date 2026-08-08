import { createReadStream } from "node:fs";
import { readFile, stat } from "node:fs/promises";
import { createServer } from "node:http";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.PORT || 4319);
const MIME = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".svg": "image/svg+xml",
};

async function runCheck() {
  const [html, css, js, pkg] = await Promise.all([
    readFile(path.join(ROOT, "index.html"), "utf8"),
    readFile(path.join(ROOT, "styles.css"), "utf8"),
    readFile(path.join(ROOT, "app.js"), "utf8"),
    readFile(path.join(ROOT, "package.json"), "utf8"),
  ]);
  const checks = [
    ["independent port 4319", /4319/.test(await readFile(path.join(ROOT, "server.mjs"), "utf8"))],
    ["independent storage key", /kaogong-workbench-theme/.test(html + js) && /kaogong-workbench-accent/.test(html + js)],
    ["theme cycle", /themeOrder = \["system", "light", "dark"\]/.test(js) && /theme-toggle/.test(html + css)],
    ["five accent swatches", (html.match(/data-accent-option=/g) || []).length === 5 && /html\[data-accent="sakura"\]/.test(css)],
    ["four fluid metric cards", (html.match(/class="metric-card/g) || []).length === 4 && /metricFluidDrift/.test(css)],
    ["material drawer controls", /materialOverlay/.test(html + js) && /materialOpacity/.test(html) && /colorA/.test(html)],
    ["carousel interactions", /orbitModeBtn/.test(js) && /fanModeBtn/.test(js) && /carouselViewport/.test(html) && /wheel/.test(js) && /setPlaying/.test(js)],
    ["exam professional content", /国考/.test(html + js) && /省考/.test(html + js) && /行测/.test(html + js) && /申论/.test(html + js) && /进面线/.test(html + js) && /报考比/.test(html + js)],
    ["static package shape", /"start": "node server\.mjs"/.test(pkg) && /"type": "module"/.test(pkg)],
  ];
  const failed = checks.filter(([, ok]) => !ok);
  if (failed.length) throw new Error(`Failed checks: ${failed.map(([name]) => name).join(", ")}`);
  console.log(`check passed: ${checks.length} kaogong dashboard checks`);
}

if (process.argv.includes("--check")) {
  runCheck().catch((error) => {
    console.error(error.message);
    process.exit(1);
  });
} else {
createServer(async (request, response) => {
  const requested = request.url === "/" ? "/index.html" : request.url.split("?")[0];
  const filePath = path.join(ROOT, requested);

  if (!filePath.startsWith(ROOT)) {
    response.writeHead(403).end("Forbidden");
    return;
  }

  try {
    const details = await stat(filePath);
    if (!details.isFile()) throw new Error("not a file");
    response.writeHead(200, { "content-type": MIME[path.extname(filePath)] || "application/octet-stream" });
    createReadStream(filePath).pipe(response);
  } catch {
    response.writeHead(404, { "content-type": "text/plain; charset=utf-8" });
    response.end("Not found");
  }
}).listen(PORT, "127.0.0.1", () => {
  console.log(`Kaogong Workbench is running at http://127.0.0.1:${PORT}`);
});
}
