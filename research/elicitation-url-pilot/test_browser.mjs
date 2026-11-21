import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { once } from "node:events";
import { mkdtemp, readdir, readFile, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { createRequire } from "node:module";
import { createInterface } from "node:readline";
import test from "node:test";
import { fileURLToPath } from "node:url";

async function startProbe(t, {
  capabilities = { elicitation: { url: {} } },
  protocolVersion = "2025-11-25",
} = {}) {
  const temp = await mkdtemp(path.join(tmpdir(), "url-pilot-test-"));
  const fixture = fileURLToPath(new URL("stdio_probe.py", import.meta.url));
  const proc = spawn("python3", ["-I", fixture], {
    env: { ...process.env, TMPDIR: temp },
    stdio: ["pipe", "pipe", "inherit"],
  });
  const exited = once(proc, "close");
  const output = createInterface({ input: proc.stdout })[Symbol.asyncIterator]();
  t.after(async () => {
    proc.stdin.end();
    await exited;
    await rm(temp, { recursive: true });
  });

  async function rpc(msg) {
    proc.stdin.write(JSON.stringify({ jsonrpc: "2.0", ...msg }) + "\n");
    const reply = await output.next();
    assert.equal(reply.done, false, "MCP fixture exited before answering");
    return JSON.parse(reply.value);
  }

  const init = await rpc({ id: 1, method: "initialize", params: {
    protocolVersion, capabilities,
  } });
  assert.equal(init.result.protocolVersion, "2025-11-25");
  const [directory] = await readdir(temp);
  return {
    rpc,
    target: path.join(temp, directory, "public-marker.txt"),
    call: (id, name) => rpc({ id, method: "tools/call", params: { name, arguments: {} } }),
  };
}

function state(reply) {
  return reply.result.content[0].text;
}

function postMarker(url) {
  return fetch(url, {
    method: "POST",
    headers: { Origin: new URL(url).origin },
    body: "",
  });
}

test("URL flow: consent, visit, exact write, replay", { timeout: 5000 }, async (t) => {
  const { rpc, target, call } = await startProbe(t);
  const ask = await call(2, "probe_url");
  assert.equal(ask.method, "elicitation/create");
  assert.equal(ask.params.mode, "url");
  assert.equal((await postMarker(ask.params.url)).status, 409);
  await assert.rejects(readFile(target), { code: "ENOENT" });

  const accepted = await rpc({ id: ask.id, result: { action: "accept" } });
  assert.equal(state(accepted), "awaiting_browser");
  const page = await fetch(ask.params.url);
  assert.equal(page.status, 200);
  assert.match(await page.text(), /Write public marker/);
  assert.equal(state(await call(3, "probe_status")), "awaiting_browser");
  await assert.rejects(readFile(target), { code: "ENOENT" });

  assert.equal((await postMarker(ask.params.url)).status, 200);
  assert.equal(state(await call(4, "probe_status")), "saved");
  assert.equal(await readFile(target, "utf8"), "PUBLIC_SECRET_DROP_URL_PILOT\n");
  assert.equal((await postMarker(ask.params.url)).status, 409);
});

test("Chromium can submit the loopback page", {
  skip: process.env.RUN_BROWSER_TEST !== "1",
  timeout: 20000,
}, async (t) => {
  const { chromium } = createRequire(import.meta.url)("playwright");
  const { rpc, target, call } = await startProbe(t);
  const ask = await call(2, "probe_url");
  assert.equal(state(await rpc({ id: ask.id, result: { action: "accept" } })), "awaiting_browser");
  const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH });
  t.after(() => browser.close());
  const page = await browser.newPage();
  assert.equal((await page.goto(ask.params.url)).status(), 200);
  await page.getByRole("button", { name: "Write public marker" }).click();
  await page.getByRole("heading", { name: "Public marker saved" }).waitFor();
  assert.equal(state(await call(3, "probe_status")), "saved");
  assert.equal(await readFile(target, "utf8"), "PUBLIC_SECRET_DROP_URL_PILOT\n");
});

test("cancel closes the write gate", { timeout: 5000 }, async (t) => {
  const { rpc, target, call } = await startProbe(t);
  const ask = await call(2, "probe_url");
  assert.equal(state(await rpc({ id: ask.id, result: { action: "cancel" } })), "cancelled");
  const response = await postMarker(ask.params.url);
  assert.equal(response.status, 409);
  await assert.rejects(readFile(target), { code: "ENOENT" });
  assert.equal(state(await call(3, "probe_status")), "cancelled");
});

test("form-only capability cannot trigger URL mode", { timeout: 5000 }, async (t) => {
  const { call, target } = await startProbe(t, { capabilities: { elicitation: { form: {} } } });
  const reply = await call(2, "probe_url");
  assert.equal(reply.result.isError, true);
  assert.equal(state(reply), "url_not_advertised");
  await assert.rejects(readFile(target), { code: "ENOENT" });
});

test("an older initial version does not override advertised URL capability", { timeout: 5000 }, async (t) => {
  const { rpc, call } = await startProbe(t, { protocolVersion: "2025-06-18" });
  const ask = await call(2, "probe_url");
  assert.equal(ask.params.mode, "url");
  const reply = await rpc({ id: ask.id, result: { action: "cancel" } });
  assert.equal(state(reply), "cancelled");
});
