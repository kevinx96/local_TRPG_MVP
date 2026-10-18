import { writeFile } from "node:fs/promises";
import { join } from "node:path";

const [port, origin, output] = process.argv.slice(2);
const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws = new WebSocket(pages.find(page => page.type === "page").webSocketDebuggerUrl);
await new Promise(resolve => ws.addEventListener("open", resolve, { once: true }));
let sequence = 0;
const pending = new Map();
ws.addEventListener("message", event => {
  const data = JSON.parse(event.data);
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
const views = [
  ["start-1280x800", 1280, 800, "start"], ["start-800x480", 800, 480, "start"],
  ["start-375x812", 375, 812, "start", true],
  ["castle-town-1280x800", 1280, 800, "castle_town"],
  ["castle-town-800x480", 800, 480, "castle_town"],
  ["castle-town-hover-800x480", 800, 480, "castle_town", false, true],
  ["magic-shop-1280x800", 1280, 800, "magic_shop"],
  ["magic-shop-touch-375x812", 375, 812, "magic_shop", true],
];
try {
  await cdp("Page.enable");
  await cdp("Emulation.setFocusEmulationEnabled", { enabled: true });
  for (const [view, width, height, location, touch = false, hover = false] of views) {
    checks = [];
    await cdp("Emulation.setDeviceMetricsOverride", { width, height, deviceScaleFactor: 1, mobile: touch });
    await cdp("Emulation.setTouchEmulationEnabled", { enabled: touch });
    await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
    await cdp("Page.navigate", { url: `${origin}/?capture=${view}` });
    await waitFor(`location.search === '?capture=${view}' && document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'`);
    await evaluate("Promise.all([...document.images].map(img => img.decode().catch(() => {})))");
    check(await evaluate(`innerWidth === ${width} && innerHeight === ${height}`), "exact viewport");
    if (location === "start") {
      check(await evaluate("els.startTitle.textContent === '紅き邪竜イグニス' && els.scenarioSelect.value === 'dragon_rpg_hybrid.json'"), "story title and default Hybrid");
      check(await evaluate("getComputedStyle(document.querySelector('.start-bg')).animationName === 'none'"), "reduced motion");
      check(await evaluate("document.querySelector('#configDropdown').contains(els.scenarioSelect) && document.querySelector('#configDropdown').contains(els.backendStatus) && getComputedStyle(document.querySelector('#configDropdown')).display === 'none'"), "scenario and model status in closed settings");
      check(await evaluate(`(() => { const cards = [...document.querySelectorAll('.char-card')].map(c => c.getBoundingClientRect()); return new Set(cards.map(c => Math.round(c.top))).size === ${width < 720 ? 2 : 1}; })()`), "responsive character rows");
      check(await evaluate("(() => { const images = [...document.querySelectorAll('.char-card img')].map(i=>i.src); const input = document.querySelector('[name=heroGender][value=女勇者]'); input.checked = true; input.dispatchEvent(new Event('change')); const changed = [...document.querySelectorAll('.char-card img')].map(i=>i.src); const correct = changed[0] !== images[0] && changed.slice(1).every((v,i)=>v===images[i+1]); document.querySelector('[name=heroGender][value=男勇者]').checked = true; input.dispatchEvent(new Event('change')); return correct; })()"), "gender switches only the available portrait variant");
      check(await evaluate("(() => { const card = document.querySelector('[data-char-id=thief]'); card.click(); const good = state.selectedCharacterId === 'thief' && card.getAttribute('aria-pressed') === 'true'; document.querySelector('[data-char-id=hero]').click(); return good; })()"), "character selection");
      check(await evaluate("(() => { const rect = els.startButton.getBoundingClientRect(); return rect.top >= 0 && rect.bottom <= innerHeight; })()"), "start button fits viewport");
    } else {
      await evaluate(`(async () => { const session = await fetchJson('/fixture?location=${location}'); els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session); revealPendingChoices(); })()`);
      await evaluate("Promise.all([...document.images].filter(i=>i.getAttribute('src')).map(img=>img.decode().catch(()=>{})))");
      await new Promise(resolve => setTimeout(resolve, 300));
      check(await evaluate(`matchMedia('(hover: none)').matches === ${touch}`), "correct pointer media query");
      const rectsBefore = await evaluate("[...els.choicesList.children].map(c=>c.getBoundingClientRect().height)");
      if (touch) {
        check(await evaluate("getComputedStyle(els.choiceDescription).display === 'none' && getComputedStyle(document.querySelector('.choice-preview')).display !== 'none'"), "touch keeps inline descriptions");
      } else {
        check(await evaluate("getComputedStyle(document.querySelector('.choice-preview')).display === 'none'"), "desktop descriptions hidden in cards");
        await evaluate("document.querySelectorAll('.choice-card')[1].focus()");
        check(await evaluate("els.choiceDescription.textContent === document.activeElement.dataset.description"), "keyboard focus updates fixed description");
        await cdp("Input.dispatchKeyEvent", { type: "keyDown", key: "ArrowDown", code: "ArrowDown" });
        check(await evaluate("document.activeElement.dataset.choiceIndex === '2'"), "arrow key moves focus");
        if (hover) {
          await evaluate("document.activeElement.blur()");
          const rect = await evaluate("(() => { const r = document.querySelector('[data-action-id=go_dark_forest]').getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2}; })()");
          await cdp("Input.dispatchMouseEvent", { type: "mouseMoved", ...rect });
          check(await evaluate("els.choiceDescription.textContent === '第2章へ進みます'"), "real hover updates description");
        }
        if (location === "castle_town") {
          check(await evaluate("els.choicesList.children.length >= 6 && els.choicesList.scrollHeight <= els.choicesList.clientHeight + 1"), "at least six choices fit without scrolling");
        }
        const rectsAfter = await evaluate("[...els.choicesList.children].map(c=>c.getBoundingClientRect().height)");
        check(JSON.stringify(rectsBefore) === JSON.stringify(rectsAfter), "focus and hover do not change row heights");
        check(await evaluate("els.choicesList.scrollWidth <= els.choicesList.clientWidth"), "no horizontal choice scrolling");
      }
      if (location === "magic_shop") {
        check(await evaluate("(() => { const card = document.querySelector('.unknown-choice'); return card && card.querySelector('.choice-text').textContent === '？？？' && card.getAttribute('aria-disabled')==='true' && !card.querySelector('.choice-risk,.choice-group-hint') && getComputedStyle(card).borderTopStyle==='dashed'; })()"), "unknown card has no label and cannot be selected");
        await evaluate("document.querySelector('.unknown-choice').focus(); document.querySelector('.unknown-choice').click()");
        check(await evaluate("state.session.current_location === 'magic_shop' && !state.turnBusy"), "disabled card remains in place");
        if (!touch) check(await evaluate("els.choiceDescription.textContent === 'まだ知らない何かが必要なようだ。'"), "disabled reason in footer");
        if (!touch) check(await evaluate("getComputedStyle(document.querySelector('.unknown-choice')).outlineStyle === 'dashed'"), "unknown focus keeps dashed outline");
      }
    }
    check(await evaluate("document.documentElement.scrollWidth <= innerWidth"), "no horizontal overflow");
    await new Promise(resolve => setTimeout(resolve, 300));
    const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
    await writeFile(join(output, `${view}.png`), Buffer.from(screenshot.data, "base64"));
    results.push({ view, width, height, touch, ok: true, checks });
    console.log(`${view}: ${checks.length} checks passed`);
  }
} catch (error) {
  const layout = await evaluate("({viewport:[innerWidth,innerHeight], startButton:els.startButton.getBoundingClientRect().toJSON(), content:document.querySelector('.start-content').getBoundingClientRect().toJSON(), active:document.activeElement.outerHTML.slice(0,500), description:els.choiceDescription.textContent, focused:document.hasFocus()})");
  const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  await writeFile(join(output, "failure.png"), Buffer.from(screenshot.data, "base64"));
  results.push({ ok: false, checks, error: String(error), layout });
  console.error(error);
  process.exitCode = 1;
} finally {
  await writeFile(join(output, "checks.json"), JSON.stringify(results, null, 2) + "\n");
  ws.send(JSON.stringify({ id: ++sequence, method: "Browser.close" }));
  ws.close();
}
