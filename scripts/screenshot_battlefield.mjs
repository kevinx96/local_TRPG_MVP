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
const views = ["old_battlefield", "ruined_watchtower", "ghoul_marsh", "grave_chapel",
  "zebok_entry", "cursed_bones", "plain_bones", "zebok_plain"];
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  for (const view of views) {
    checks = [];
    await cdp("Page.navigate", { url: `${origin}/?capture=${view}` });
    await waitFor(`location.search === '?capture=${view}' && document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'`);
    await evaluate(`(async () => { const session = await fetchJson('/031-fixture?view=${view}'); els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session); revealPendingChoices(); })()`);
    check(await evaluate("(async () => { const image = new Image(); image.src = state.session.location_background_image; await image.decode(); return image.naturalWidth > 0; })()"), "background decodes");
    await evaluate("Promise.all([...document.images].filter(i=>i.getAttribute('src')).map(i=>i.decode().catch(()=>{})))");
    await new Promise(resolve => setTimeout(resolve, 200));
    check(await evaluate("!state.session.in_combat"), "arrival does not auto-start combat");
    check(await evaluate("[...document.images].filter(i=>i.getAttribute('src') && i.getClientRects().length).every(i=>i.complete && i.naturalWidth>0)"), "visible portraits decode");
    check(await evaluate("els.messageText.textContent.length > 0"), "authored narration visible");
    check(await evaluate("els.choicesList.children.length > 0 && els.choicesList.scrollWidth <= els.choicesList.clientWidth"), "choices visible without horizontal scrolling");
    check(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "no horizontal page overflow");
    if (view === "cursed_bones" || view === "plain_bones") {
      check(await evaluate(`!!document.querySelector('[data-action-id=show_curse_to_skeletons]') === ${view === "cursed_bones"}`), "curse choice matches inventory");
      if (view === "cursed_bones") {
        check(await evaluate("document.querySelector('[data-action-id=show_curse_to_skeletons]').textContent.includes('呪いの品を掲げて通る')"), "authored curse label");
        await evaluate("document.querySelector('[data-action-id=show_curse_to_skeletons]').focus()");
      }
    }
    if (view.startsWith("zebok")) {
      check(await evaluate("els.npcPortrait.src.endsWith('/npc_zebok_merchant.png') && els.spriteLayer.classList.contains('dialogue-mode') && getComputedStyle(els.npcPortrait).display !== 'none'"), "Zebok arrival portrait visible");
      check(await evaluate(`els.messageText.textContent.includes('${view === "zebok_entry" ? "代価のことは" : "ここは死者の道"}')`), "correct entry branch");
    }
    if (view === "grave_chapel") {
      check(await evaluate("!state.session.dialogue_portrait_image && !els.messageText.textContent.includes('ここは死者の道')"), "repeat arrival does not repeat Zebok");
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
