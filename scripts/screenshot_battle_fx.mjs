import { mkdir, writeFile } from "node:fs/promises";
import { join } from "node:path";

const [port, origin, output] = process.argv.slice(2);
const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws = new WebSocket(pages.find(page => page.type === "page").webSocketDebuggerUrl);
await new Promise(resolve => ws.addEventListener("open", resolve, { once: true }));
let sequence = 0;
const pending = new Map();
ws.addEventListener("message", event => {
  const data = JSON.parse(event.data);
  if (!pending.has(data.id)) return;
  const { resolve, reject } = pending.get(data.id);
  pending.delete(data.id);
  data.error ? reject(new Error(JSON.stringify(data.error))) : resolve(data.result);
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
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const checks = [];
function check(value, label) {
  if (!value) throw new Error(label);
  checks.push(label);
}
async function screenshot(file, format = "png") {
  const result = await cdp("Page.captureScreenshot", { format, ...(format === "jpeg" ? {quality: 80} : {}), captureBeyondViewport: false });
  await writeFile(join(output, file), Buffer.from(result.data, "base64"));
}
const errors = [];
ws.addEventListener("message", event => {
  const data = JSON.parse(event.data);
  if (data.method === "Runtime.exceptionThrown") errors.push(data.params.exceptionDetails.text);
});
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setFocusEmulationEnabled", { enabled: true });
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
  await cdp("Page.navigate", { url: origin });
  for (let i = 0; i < 200; i++) {
    if (await evaluate("document.readyState === 'complete' && typeof state !== 'undefined' && document.querySelectorAll('.char-card').length === 4")) break;
    await delay(50);
  }
  check(await evaluate("typeof fetchJson === 'function' && document.querySelectorAll('.char-card').length === 4"), "local capture page ready");
  await evaluate(`(async () => { window.examples = await fetchJson('/fixtures-030');
    window.domResult = () => ({
      bars: [...els.combatScreen.querySelectorAll('.combat-resource')].map(row => [row.querySelector('strong').textContent, row.querySelector('b').style.width]),
      logs: [...els.combatLog.children].map(row => row.textContent),
      portraits: [...els.combatEnemies.querySelectorAll('img')].map(img => img.getAttribute('src')),
      enemies: [...els.combatEnemies.children].map(node => [node.dataset.combatTarget, node.className, node.disabled]),
      result: [els.combatResult.style.display, els.combatResultTitle.textContent, els.combatResultText.textContent],
    });
    window.show = session => { state.combatBusy = false; state.combatIntroSeenId = session.combat?.id || ''; els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(structuredClone(session)); };
    window.begin = example => { state.combatBusy = true; els.combatScreen.classList.add('busy'); window.startedAt = performance.now(); window.done = false;
      window.playing = playCombatEvents(example.before, example.after).then(() => { window.duration = performance.now() - startedAt; state.combatBusy = false; renderSession(structuredClone(example.after)); window.done = true; }); };
  })()`);
  for (const name of ["normal", "critical", "miss", "fire", "ice", "holy", "rainbow", "heavy", "heal", "buff", "knockout", "phase", "reduced"]) {
    await mkdir(join(output, "frames", name), { recursive: true });
    await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: name === "reduced" ? "reduce" : "no-preference" }] });
    await evaluate(`show(examples.${name}.after); window.expected = domResult(); show(examples.${name}.before)`);
    await evaluate("Promise.all([...document.images].filter(img=>img.getAttribute('src')).map(img=>img.decode().catch(()=>{})))");
    // Preload the second phase without changing the visible DOM.
    if (name === "phase") await evaluate("Promise.all(examples.phase.after.combat.enemies.map(e=>{const img=new Image(); img.src=e.image;return img.decode();}))");
    await delay(550); // Let the existing background crossfade settle before the first frame.
    check(await evaluate("[...els.combatActions.querySelectorAll('button')].every(b=>b.getAttribute('aria-label')?.includes(b.querySelector('strong').textContent))"), `${name}: readable action names`);
    await screenshot(`frames/${name}/0.png`);
    await evaluate(`begin(examples.${name}); void 0`);
    await delay(name === "phase" ? 280 : 65);
    const active = await evaluate(`({numbers: [...document.querySelectorAll('.combat-number span')].map(n=>n.textContent),
      announce: document.querySelector('#combatAnnouncement').textContent,
      ghost: !!document.querySelector('.combat-phase-ghost'),
      delays: document.querySelectorAll('.combat-delay-bar').length,
      properties: els.combatScreen.getAnimations({subtree:true}).flatMap(a=>a.effect.getKeyframes().flatMap(f=>Object.keys(f))),
      shake: els.gameScreen.getAnimations().length,
      effects: [...document.querySelectorAll('.combat-impact')].map(n=>n.className),
      logCount: els.combatLog.children.length})`);
    if (name === "critical") {
      check(active.numbers.some(n=>n.includes("CRITICAL")), "critical: flag renders enlarged gold number");
      check(await evaluate("getComputedStyle(document.querySelector('.combat-number')).fontSize === '39px' && document.querySelector('.combat-number').classList.contains('critical')"), "critical: number size is 1.5 times normal");
    }
    if (name === "miss") check(active.numbers.includes("MISS"), "miss: event renders MISS");
    if (name === "heal") check(active.numbers.some(n=>n.startsWith("+")), "heal: positive number and live announcement");
    if (name === "heavy") check(active.shake > 0, "heavy: engine flag starts screen shake");
    if (name === "phase") check(active.ghost, "phase: old and new forms overlap");
    if (["fire", "ice", "holy", "rainbow"].includes(name)) check(active.effects.some(e=>e.includes(`impact-${name}`)), `${name}: matching generated effect`);
    if (name === "normal") {
      check(active.delays > 0, "normal: HP decrease has delayed bar");
      check(await evaluate("els.combatLog.lastElementChild.textContent.includes(examples.normal.after.combat.events[0].text)"), "normal: damage log appears with effect");
    }
    if (name === "reduced") {
      check(active.delays === 0 && active.shake === 0 && active.effects.length === 0, "reduced: no delayed bar, shake or particles");
      check(await evaluate("els.combatScreen.getAnimations({subtree:true}).every(a=>new Set(a.effect.getKeyframes().map(f=>f.transform).filter(Boolean)).size <= 1)"), "reduced: no lunge, dodge or floating motion");
    }
    if (!["buff", "phase"].includes(name)) check(Boolean(active.announce), `${name}: live announcement`);
    await screenshot(`frames/${name}/1.png`);
    await delay(230);
    await screenshot(`frames/${name}/2.png`);
    await evaluate("playing");
    await screenshot(`frames/${name}/3.png`);
    check(await evaluate("JSON.stringify(domResult()) === JSON.stringify(expected)"), `${name}: final HP/MP, log lines, portraits and result equal immediate render`);
    check(await evaluate("duration <= 1450"), `${name}: <=1.4s timeline (50ms browser scheduling tolerance)`);
    check(await evaluate("!state.combatPlayback && !document.querySelector('#combatFxLayer').children.length && !document.querySelector('.combat-delay-bar')"), `${name}: temporary DOM cleaned up`);
    console.log(`${name}: passed`);
  }
  for (const name of ["long_response", "defeat"]) {
    await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "no-preference" }] });
    await evaluate(`show(examples.${name}.after); expected=domResult(); show(examples.${name}.before); begin(examples.${name}); void 0`);
    if (name === "defeat") {
      await delay(960);
      check(await evaluate("!done && els.combatResult.style.display === 'none'"), "defeat: result waits 300ms after effect completion");
    }
    await evaluate("playing");
    check(await evaluate("duration <= 1450 && JSON.stringify(domResult()) === JSON.stringify(expected)"), `${name}: complete action <=1.4s and exact final DOM`);
    if (name === "long_response") check(await evaluate("examples.long_response.after.combat.events.length >= 25"), "long response: at least 24 hits and enemy reply");
  }
  for (const mode of ["click", "space"]) {
    await evaluate("show(examples.phase.before); show(examples.phase.after); expected=domResult(); show(examples.phase.before); begin(examples.phase); void 0");
    if (mode === "click") await cdp("Input.dispatchMouseEvent", { type: "mousePressed", x: 700, y: 300, button: "left", clickCount: 1 });
    if (mode === "click") await cdp("Input.dispatchMouseEvent", { type: "mouseReleased", x: 700, y: 300, button: "left", clickCount: 1 });
    else await cdp("Input.dispatchKeyEvent", { type: "keyDown", key: " ", code: "Space", windowsVirtualKeyCode: 32 });
    await evaluate("playing");
    check(await evaluate("duration < 500 && JSON.stringify(domResult()) === JSON.stringify(expected)"), `${mode}: skip applies exact final state`);
    await delay(1000);
    check(await evaluate("JSON.stringify(domResult()) === JSON.stringify(expected) && !document.querySelector('#combatFxLayer').children.length"), `${mode}: no late events after skip`);
  }
  await evaluate("show(examples.inn); revealPendingChoices(); window.originalPortrait=els.npcPortrait.getAttribute('src'); document.querySelector('[data-action-id=ask_ian]').click()");
  check(await evaluate("els.npcPortrait.getAttribute('src') === '/static/images/npc_ian.png' && state.choiceStack.length === 1"), "portrait: parent click immediately selects Ian");
  await evaluate("document.querySelector('.choice-back').click()");
  check(await evaluate("els.npcPortrait.getAttribute('src') === originalPortrait && state.choiceStack.length === 0"), "portrait: back restores original");
  check(await evaluate(`parentChoicePortrait({children:[{portrait_image:'a'}, {}, {portrait_image:'a'}]}) === 'a'
    && parentChoicePortrait({children:[{portrait_image:'a'}, {portrait_image:'b'}]}) === null`), "portrait: identical child fallback and mixed children");
  await evaluate(`state.pendingChoices=[{text:'イアン', portrait_image:'/static/images/npc_ian.png', children:[{text:'ロビン',portrait_image:'/static/images/npc_robin.png',children:[{text:'戻る'}]}]}]; renderChoices(state.pendingChoices); document.querySelector('[data-choice-index="0"]').click(); document.querySelector('[data-choice-index="0"]').click()`);
  check(await evaluate("els.npcPortrait.getAttribute('src') === '/static/images/npc_robin.png'"), "portrait: nested parent preview");
  await evaluate("document.querySelector('.choice-back').click()");
  check(await evaluate("els.npcPortrait.getAttribute('src') === '/static/images/npc_ian.png'"), "portrait: nested back restores parent");
  await evaluate("clearPendingChoices()");
  check(await evaluate("els.npcPortrait.getAttribute('src') === originalPortrait"), "portrait: collapse restores original");
  check(await evaluate("classifyRisk('不明') === 'check'"), "risk: unknown uses existing neutral style");
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "no-preference" }] });
  await mkdir(join(output, "video"), { recursive: true });
  const video = [];
  const started = performance.now();
  let frame = 0;
  async function record(ms) {
    const until = performance.now() + ms;
    while (performance.now() < until) {
      const file = `video/${String(frame++).padStart(4, "0")}.jpg`;
      const time = performance.now() - started;
      await screenshot(file, "jpeg");
      video.push({ file, ms: time });
      await delay(Math.max(0, 100 - (performance.now() - started - time)));
    }
  }
  await evaluate("(async()=>{show(await fetchJson('/guard-session')); state.combatIntroSeenId=''; renderCombatIntro(state.session.combat);})()");
  await record(1500);
  await evaluate("els.combatIntroContinue.click()");
  const turnCount = await evaluate("examples.guard_battle.length");
  for (let turn = 0; turn < turnCount; turn++) {
    await evaluate(`state.combatActionTab = examples.guard_battle[${turn}].action === 'defend' ? 'tactics' : 'attack'; renderCombatActions(state.combatActions); document.querySelector('[data-combat-action-type="' + examples.guard_battle[${turn}].action + '"]').click(); void 0`);
    await record(1800);
    check(await evaluate("!state.combatBusy && !state.combatPlayback"), `guard battle turn ${turn + 1}: actual button and HTTP action completed`);
  }
  await record(Math.max(700, 9500 - (performance.now() - started)));
  check(await evaluate("state.session.combat.status === 'victory' && getComputedStyle(els.combatResult).display !== 'none'"), "guard battle: complete engine-resolved victory");
  await writeFile(join(output, "video-frames.json"), JSON.stringify(video, null, 2) + "\n");
  check(errors.length === 0, "no browser exceptions");
  await writeFile(join(output, "checks.json"), JSON.stringify({ ok: true, checks, errors, guardTurns: turnCount }, null, 2) + "\n");
  console.log(`${checks.length} browser checks passed`);
} catch (error) {
  await screenshot("failure.png");
  await writeFile(join(output, "checks.json"), JSON.stringify({ ok: false, checks, errors, error: String(error) }, null, 2) + "\n");
  console.error(error);
  process.exitCode = 1;
} finally {
  ws.send(JSON.stringify({ id: ++sequence, method: "Browser.close" }));
  ws.close();
}
