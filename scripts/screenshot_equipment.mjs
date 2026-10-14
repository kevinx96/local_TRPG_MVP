import { writeFile } from "node:fs/promises";
import { join } from "node:path";

const [port, origin, output] = process.argv.slice(2);
const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws = new WebSocket(pages.find(page => page.type === "page").webSocketDebuggerUrl);
await new Promise(resolve => ws.addEventListener("open", resolve, { once: true }));
let sequence = 0;
const pending = new Map();
const errors = [];
ws.addEventListener("message", event => {
  const data = JSON.parse(event.data);
  if (data.method === "Runtime.exceptionThrown") errors.push(data.params.exceptionDetails);
  if (pending.has(data.id)) {
    const { resolve, reject } = pending.get(data.id);
    pending.delete(data.id);
    data.error ? reject(new Error(JSON.stringify(data.error))) : resolve(data.result);
  }
});
function cdp(method, params = {}) {
  const id = ++sequence;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    ws.send(JSON.stringify({ id, method, params }));
  });
}
async function evaluate(expression) {
  const result = await cdp("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (result.exceptionDetails) throw new Error(result.exceptionDetails.exception?.description || JSON.stringify(result.exceptionDetails));
  return result.result.value;
}
async function waitFor(expression) {
  for (let attempt = 0; attempt < 200; attempt++) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error(`Timeout: ${expression}`);
}
const results = [];
let checks;
function check(value, label) {
  if (!value) throw new Error(label);
  checks.push(label);
}
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1080, deviceScaleFactor: 1, mobile: false });
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  checks = [];
  await cdp("Page.navigate", { url: origin });
  await waitFor("document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'");
  await evaluate("(async () => { const session = await fetchJson('/032-fixture'); els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session); })()");
  await evaluate("els.menuToggleBtn.click()");
  for (const id of ["adamantite_armor", "ice_iron_greatsword", "ruby_charm"]) {
    await evaluate(`document.querySelector('[data-item-id="${id}"] .item-header').click()`);
  }
  check(await evaluate("['武器','防具','装飾品'].every(label => [...els.inventory.querySelectorAll('.item-name .item-qty')].some(tag=>tag.textContent===label))"), "three explicit slot labels");
  for (const [id, oldName] of [["adamantite_armor", "革の鎧"], ["ice_iron_greatsword", "鉄の剣"], ["ruby_charm", "氷の護符(活性化済)"]]) {
    check(await evaluate(`document.querySelector('[data-item-id="${id}"] .item-use').textContent === '装備する（${oldName}と入れ替え）'`), `${id}: replacement button`);
  }
  check(await evaluate("!document.querySelector('[data-item-id=ice_charm] .item-use') && !document.querySelector('[data-item-id=ice_charm] .equipped-tag')"), "inactive charm is not equippable");
  await evaluate("els.inventory.scrollIntoView({block:'start'})");
  await new Promise(resolve => setTimeout(resolve, 350));
  check(await evaluate("els.inventory.scrollWidth <= els.inventory.clientWidth && document.documentElement.scrollWidth <= innerWidth"), "no horizontal overflow");
  let shot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  await writeFile(join(output, "inventory-slots.png"), Buffer.from(shot.data, "base64"));
  await evaluate("document.querySelector('[data-item-id=adamantite_armor] .item-use').click()");
  await waitFor("!state.serviceBusy && state.character.equipment.includes('アダマンタイトの鎧')");
  check(await evaluate("!state.character.equipment.includes('革の鎧') && state.character.inventory.some(i=>i.name==='革の鎧')"), "replaced armor remains in inventory");
  check(await evaluate("document.querySelector('[data-item-id=adamantite_armor] .equipped-tag').textContent === '装備中'"), "new armor marked equipped");
  check(await evaluate("els.systemLogs.textContent.includes('革の鎧を外し、アダマンタイトの鎧を装備した。')"), "replacement log from engine");
  await evaluate("els.inventory.scrollIntoView({block:'start'})");
  await new Promise(resolve => setTimeout(resolve, 350));
  shot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  await writeFile(join(output, "inventory-after-swap.png"), Buffer.from(shot.data, "base64"));
  check(errors.length === 0, "no browser exceptions");
  results.push({ width: 1440, height: 1080, ok: true, checks });
  console.log(`equipment: ${checks.length} checks passed`);
} catch (error) {
  const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  await writeFile(join(output, "failure.png"), Buffer.from(screenshot.data, "base64"));
  results.push({ ok: false, checks, error: String(error), browserErrors: errors });
  console.error(error);
  process.exitCode = 1;
} finally {
  await writeFile(join(output, "checks.json"), JSON.stringify(results, null, 2) + "\n");
  ws.send(JSON.stringify({ id: ++sequence, method: "Browser.close" }));
  ws.close();
}
