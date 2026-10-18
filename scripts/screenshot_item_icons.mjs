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
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  for (const mobile of [false, true]) for (const view of ["inventory", "shop", "combat"]) {
    checks = [];
    const width = mobile ? 390 : 1440;
    const height = mobile ? 844 : 1080;
    const capture = `${view}${mobile ? "-mobile" : ""}`;
    const root = view === "inventory" ? "#inventory" : view === "shop" ? "#shopItems" : "#combatActions";
    await cdp("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile });
    await cdp("Page.navigate", { url: `${origin}/?capture=${capture}` });
    await waitFor(`location.search === '?capture=${capture}' && document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'`);
    await evaluate(`(async () => {
      const session = await fetchJson('/036-fixture?view=${view === "combat" ? "combat" : "inventory"}');
      els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session); revealPendingChoices();
    })()`);
    if (view === "inventory") {
      await evaluate("els.menuToggleBtn.click(); els.inventory.scrollIntoView({block:'start'})");
      await waitFor("getComputedStyle(els.menuOverlay).display !== 'none'");
      await evaluate("document.querySelector('#inventory .item-header img').click()");
      check(await evaluate("document.querySelector('#inventory .item-header').getAttribute('aria-expanded') === 'true'"), "clicking icon expands inventory details");
      await evaluate("document.querySelector('#inventory .item-header').click()");
    } else if (view === "shop") {
      await evaluate("(async () => { state.shop = await fetchJson('/036-fixture?view=shop'); document.querySelector('#shopOverlay').style.display='flex'; document.querySelector('#shopLine').textContent=state.shop.greeting; renderShop(); })()");
      await evaluate("document.querySelectorAll('#shopItems .shop-row')[1].click()");
      check(await evaluate("document.querySelectorAll('#shopItems .shop-row')[1].getAttribute('aria-pressed') === 'true'"), "shop selection works with icon");
      await evaluate("document.querySelector('#shopSellTab').click()");
      check(await evaluate("document.querySelectorAll('#shopItems .item-icon').length === state.shop.sell_items.length"), "sell rows include inline equipment icons");
      await evaluate("document.querySelector('#shopBuyTab').click()");
    } else {
      await evaluate("els.combatIntroContinue.click(); document.querySelector('[data-combat-tab=item]').click()");
      await waitFor("!els.combatScreen.classList.contains('intro-active')");
      check(await evaluate("state.combatActionTab === 'item'"), "combat item tab opens");
      await evaluate("document.querySelector('[data-combat-tab=skill]').click()");
      check(await evaluate("!els.combatActions.querySelector('.item-icon')"), "skills retain original appearance");
      await evaluate("document.querySelector('[data-combat-tab=item]').click()");
    }
    await evaluate(`Promise.all([...document.querySelectorAll('${root} .item-icon')].map(image => image.decode()))`);
    const count = await evaluate(`document.querySelectorAll('${root} .item-icon').length`);
    const expected = await evaluate(view === "inventory" ? "state.character.inventory.length"
      : view === "shop" ? "state.shop.items.length" : "state.session.combat.actions.filter(a=>a.type==='item').length");
    check(count === expected && count > 0, "every row has an icon");
    check(await evaluate(`[...document.querySelectorAll('${root} .item-icon')].every(i=>i.complete && i.naturalWidth===128 && i.width===32 && i.height===32 && i.alt==='')`), "128px PNGs display at 32px with decorative alt");
    check(await evaluate(`document.querySelector('${root}').scrollWidth <= document.querySelector('${root}').clientWidth`), "item list has no horizontal overflow");
    check(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "no horizontal page overflow");
    await evaluate("showNotification(state.character.inventory[0].name)");
    check(await evaluate("document.querySelector('#notifications').textContent.includes(state.character.inventory[0].name) && !document.querySelector('#notifications img')"), "notifications remain text only");
    await evaluate("document.querySelector('#notifications').replaceChildren()");

    // Exercise missing fields and failed requests through each real renderer.
    const data = view === "inventory" ? "state.character.inventory" : view === "shop" ? "state.shop.items" : "state.session.combat.actions.filter(a=>a.type==='item')";
    const render = view === "inventory" ? "renderInventory(state.character.inventory)" : view === "shop" ? "renderShop()" : "renderCombatActions(state.session.combat.actions)";
    await evaluate(`window.iconProbe = {item:(${data})[0], icon:(${data})[0].icon}; delete window.iconProbe.item.icon; ${render}`);
    check(await evaluate(`document.querySelectorAll('${root} .item-icon').length === ${count - 1}`), "missing optional icon keeps text row");
    await evaluate(`window.iconProbe.item.icon='/static/images/036-missing.png'; ${render}`);
    await waitFor(`document.querySelectorAll('${root} .item-icon').length === ${count - 1}`);
    check(await evaluate(`document.querySelector('${root}').textContent.includes(window.iconProbe.item.name)`), "failed image keeps item name");
    await evaluate(`window.iconProbe.item.icon=window.iconProbe.icon; ${render}; delete window.iconProbe`);
    await evaluate("Promise.all([...document.images].filter(i=>i.getAttribute('src')).map(i=>i.decode().catch(()=>{})))");
    check(errors.length === 0, "no browser exceptions");
    await new Promise(resolve => setTimeout(resolve, 250));
    const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    await writeFile(join(output, `${capture}.png`), Buffer.from(screenshot.data, "base64"));
    results.push({ view: capture, width, height, ok: true, checks });
    console.log(`${capture}: ${checks.length} checks passed`);
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
