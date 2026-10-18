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
const views = ["inn_elio", "wall_open", "entrance", "rockfall", "battle_elio", "camp", "cliff", "giant", "worm", "worm_bypass", "village"];
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  for (const view of views) {
    checks = [];
    await cdp("Page.navigate", { url: `${origin}/?capture=${view}` });
    await waitFor(`location.search === '?capture=${view}' && document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'`);
    await evaluate(`(async () => { const session = await fetchJson('/035-fixture?view=${view}'); els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session); revealPendingChoices(); })()`);
    check(await evaluate("(async () => { const image = new Image(); image.src = state.session.location_background_image; await image.decode(); return image.naturalWidth > 0; })()"), "background decodes");
    await evaluate("Promise.all([...document.images].filter(i=>i.getAttribute('src')).map(i=>i.decode().catch(()=>{})))");
    await new Promise(resolve => setTimeout(resolve, 200));
    check(await evaluate(`state.session.in_combat === ${view === "battle_elio"}`), "combat only after explicit fight");
    check(await evaluate("[...document.images].filter(i=>i.getAttribute('src') && i.getClientRects().length).every(i=>i.complete && i.naturalWidth>0)"), "visible portraits decode");
    check(await evaluate("els.messageText.textContent.length > 0"), "authored narration visible");
    if (view !== "battle_elio") check(await evaluate("els.choicesList.children.length > 0 && els.choicesList.scrollWidth <= els.choicesList.clientWidth"), "choices have no horizontal overflow");
    check(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "no horizontal page overflow");
    if (view === "inn_elio") {
      check(await evaluate("document.querySelectorAll('[data-action-id^=recruit_elio_]').length === 3"), "all three recruitment methods displayed");
      check(await evaluate("[...document.images].some(i=>i.src.endsWith('/npc_elio.png') && i.getClientRects().length)"), "Elio portrait visible");
      check(await evaluate("document.querySelector('[data-action-id=recruit_elio_gold]').textContent.includes('50G')"), "hire cost visible");
    }
    if (view === "wall_open") {
      check(await evaluate("state.session.choices.some(c=>c.action_id==='oaksdawn_east_pass_open' && c.enabled)"), "opened eastern pass selectable");
      check(await evaluate("state.session.map.maps.find(m=>m.id==='oaksdawn').nodes.some(n=>n.id==='gorge')"), "watchtower map has gorge link");
    }
    if (["entrance", "rockfall", "camp", "cliff", "giant", "worm", "worm_bypass"].includes(view)) {
      check(await evaluate("state.session.map.current_map_id==='rumbling_gorge'"), "gorge map active");
    }
    if (view === "worm" || view === "worm_bypass") {
      check(await evaluate(`state.session.choices.some(c=>c.action_id==='elio_flood_worm') === ${view === "worm_bypass"}`), "bypass depends on active Elio");
      if (view === "worm_bypass") check(await evaluate("document.querySelector('[data-action-id=elio_flood_worm]').textContent.includes('エリオの水で巣穴を満たす')"), "bypass option visibly rendered");
    }
    if (view === "battle_elio") {
      await evaluate("els.combatIntroContinue.click()");
      await waitFor("!els.combatScreen.classList.contains('intro-active')");
      check(await evaluate("state.session.companion.id==='hydromancer_elio' && !els.companionInfo.hidden"), "Elio present in gorge battle");
      check(await evaluate("els.combatLog.textContent.includes('水刃')"), "water blade shown in combat log");
      check(await evaluate("state.session.combat.enemies.every(e=>e.tags.includes('earth') && e.resistances.water===1.5 && e.resistances.physical===0.6)"), "runtime earth resistances correct");
    }
    if (view === "village") {
      check(await evaluate("state.session.current_location==='village' && !state.session.flags['reward_claimed:gorge_worm_lair']"), "bypass reaches refuge without boss drop");
    }
    check(errors.length === 0, "no browser exceptions");
    const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    await writeFile(join(output, `${view}.png`), Buffer.from(screenshot.data, "base64"));
    results.push({ view, width: 1280, height: 800, ok: true, checks });
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
