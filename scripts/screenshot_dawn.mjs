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
const views = ["workshop", "inventory", "wall", "waterway", "water_gate", "inventory_mobile"];
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  for (const view of views) {
    const mobile = view.endsWith("mobile");
    const inventory = view.startsWith("inventory");
    const width = mobile ? 390 : inventory ? 1440 : 1280;
    const height = mobile ? 844 : inventory ? 1080 : 800;
    checks = [];
    await cdp("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile });
    await cdp("Page.navigate", { url: `${origin}/?capture=${view}` });
    await waitFor(`location.search === '?capture=${view}' && document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'`);
    await evaluate(`(async () => { const session = await fetchJson('/034-fixture?view=${view}'); els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session); revealPendingChoices(); })()`);
    check(await evaluate("(async () => { const image = new Image(); image.src = state.session.location_background_image; await image.decode(); return image.naturalWidth > 0; })()"), "background decodes");
    await evaluate("Promise.all([...document.images].filter(i=>i.getAttribute('src')).map(i=>i.decode().catch(()=>{})))");
    if (view === "workshop") {
      check(await evaluate("document.querySelector('[data-action-id=forge_dawn_weapon]').textContent.includes('光の紋を刻んでもらう')"), "craft choice visible");
      check(await evaluate("state.session.choices.find(c=>c.action_id==='forge_dawn_weapon').enabled !== false"), "craft requirements met");
      const point = await evaluate("(() => {const r=document.querySelector('[data-action-id=forge_dawn_weapon]').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})()");
      await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", ...point });
      await waitFor("els.choiceDescription.textContent.includes('30G')");
      check(await evaluate("els.choiceDescription.textContent.includes('聖銀')"), "material and gold cost visible");
    }
    if (inventory) {
      await evaluate("els.menuToggleBtn.click(); els.inventory.scrollIntoView({block:'start'})");
      await waitFor("getComputedStyle(els.menuOverlay).display !== 'none'");
      check(await evaluate("document.querySelectorAll('.item-icon').length === 4"), "four earned item icons shown");
      check(await evaluate("[...document.querySelectorAll('.item-icon')].every(i=>i.complete && i.naturalWidth>0 && i.width===32 && i.height===32 && i.alt==='')"), "icons decoded at 32px with decorative alt");
      check(await evaluate("[...els.inventory.querySelectorAll('.inventory-item')].some(row=>!row.querySelector('.item-icon') && row.querySelector('.item-name'))"), "legacy items without icons render");
      check(await evaluate("document.querySelector('[data-item-id=dawn_sword] .equipped-tag').textContent==='装備中'"), "crafted weapon equipped");
      check(await evaluate("els.inventory.scrollWidth <= els.inventory.clientWidth"), "inventory has no horizontal overflow");
      await evaluate("document.querySelector('[data-item-id=dawn_sword] .item-header').click()");
      check(await evaluate("document.querySelector('[data-item-id=dawn_sword] .item-header').getAttribute('aria-expanded')==='true'"), "icon row remains interactive");
      await evaluate("document.querySelector('[data-item-id=dawn_sword] .item-header').click()");
    }
    if (view === "water_gate") check(await evaluate("state.session.location_background_image.endsWith('/bg_oaksdawn_water_gate.png')"), "water gate has dedicated background");
    check(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "no page horizontal overflow");
    check(errors.length === 0, "no browser exceptions");
    await new Promise(resolve => setTimeout(resolve, 250));
    const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    await writeFile(join(output, `${view}.png`), Buffer.from(screenshot.data, "base64"));
    results.push({ view, width, height, ok: true, checks });
    console.log(`${view}: ${checks.length} checks passed`);
  }
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
