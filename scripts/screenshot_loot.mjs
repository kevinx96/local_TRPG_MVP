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
let checks = [];
function check(value, label) {
  if (!value) throw new Error(label);
  checks.push(label);
}
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1440, height: 1080, deviceScaleFactor: 1, mobile: false });
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  for (const view of ["inventory", "shop-sell", "fort-third-gate"]) {
    checks = [];
    await cdp("Page.navigate", { url: `${origin}/?capture=${view}` });
    await waitFor(`location.search === '?capture=${view}' && document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'`);
    await evaluate(`(async () => {
      const session = await fetchJson('/038-fixture?view=${view === "fort-third-gate" ? "gate" : "inventory"}');
      els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session); revealPendingChoices();
    })()`);
    if (view === "inventory") {
      await evaluate("els.menuToggleBtn.click()");
      await waitFor("getComputedStyle(els.menuOverlay).display !== 'none'");
      check(await evaluate("[...document.querySelectorAll('.inventory-group')].some(g=>g.textContent==='戦利品')"), "separate 戦利品 heading");
      check(await evaluate("state.character.inventory.filter(i=>i.category==='loot').length===11"), "all eleven loot kinds in inventory");
      check(await evaluate("[...document.querySelectorAll('#inventory .inventory-item')].filter(i=>state.character.inventory.some(a=>a.category==='loot' && a.name===i.querySelector('.item-name')?.textContent)).length===11"), "eleven visible loot rows");
      await evaluate("[...document.querySelectorAll('.inventory-group')].find(g=>g.textContent==='戦利品').scrollIntoView({block:'start'})");
    } else if (view === "shop-sell") {
      await evaluate("(async () => { state.shop = await fetchJson('/038-fixture?view=shop'); document.querySelector('#shopOverlay').style.display='flex'; document.querySelector('#shopLine').textContent=state.shop.greeting; renderShop(); document.querySelector('#shopSellTab').click(); })()");
      check(await evaluate("!document.querySelector('#shopSellTab').disabled && state.shopTab==='sell'"), "workshop sell tab enabled");
      check(await evaluate("state.shop.sell_items.every(i=>['loot','equipment'].includes(i.category))"), "workshop shows only loot and equipment");
      check(await evaluate("state.shop.sell_items.filter(i=>i.category==='loot').length===11"), "workshop accepts all loot");
      await evaluate("[...document.querySelectorAll('#shopItems .shop-row')].find(r=>r.textContent.includes('スライムの核')).click(); document.querySelector('#shopPlus').click()");
      check(await evaluate("state.shopQuantity===2 && document.querySelector('#shopDetail .shop-price').textContent==='6 G'"), "explicit price gives 6G for two slime cores");
      await evaluate("document.querySelector('#shopTrade').click()");
      await waitFor("!state.serviceBusy && state.shop.gold===106");
      check(await evaluate("state.character.inventory.find(i=>i.id==='slime_core').quantity===1"), "real sale removes two cores and adds 6G");
      check(await evaluate("state.shop.sell_items.find(i=>i.item_id==='slime_core').quantity===1"), "sell stock refreshed after transaction");
    } else {
      check(await evaluate("state.session.current_location==='goblin_fort_third_gate'"), "arrived at third-floor gate through authored route");
      check(await evaluate("!!document.querySelector('[data-action-id=regroup_from_fort_third_gate]')"), "regroup choice rendered");
      check(await evaluate("document.querySelector('[data-action-id=regroup_from_fort_third_gate]').textContent.includes('態勢を立て直すため砦を出る')"), "exact authored regroup label");
      check(await evaluate("state.session.messages.some(m=>m.text.includes('鉄門の奥から、地を揺らすような唸り声が響いてくる。'))"), "gate description includes the warning sound");
    }
    await evaluate("Promise.all([...document.images].filter(i=>i.getAttribute('src')).map(i=>i.decode().catch(()=>{})))");
    check(await evaluate("[...document.querySelectorAll('.item-icon')].every(i=>i.complete && i.naturalWidth===128)"), "item icons loaded at native 128px");
    check(await evaluate("document.documentElement.scrollWidth<=innerWidth"), "no horizontal page overflow");
    check(errors.length === 0, "no browser exceptions");
    await new Promise(resolve => setTimeout(resolve, 250));
    const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    await writeFile(join(output, `${view}.png`), Buffer.from(screenshot.data, "base64"));
    results.push({ view, width: 1440, height: 1080, ok: true, checks });
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
