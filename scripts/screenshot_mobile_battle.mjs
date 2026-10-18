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
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function waitFor(expression) {
  for (let i = 0; i < 200; i++) {
    if (await evaluate(expression)) return;
    await delay(50);
  }
  throw new Error(`Timeout: ${expression}`);
}
const checks = [];
function check(value, label) {
  if (!value) throw new Error(label);
  checks.push(label);
}
async function screenshot(name) {
  const result = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  await writeFile(join(output, `${name}.png`), Buffer.from(result.data, "base64"));
}
async function click(selector) {
  const point = await evaluate(`(() => {const r=document.querySelector(${JSON.stringify(selector)}).getBoundingClientRect(); return {x:r.x+r.width/2,y:r.y+r.height/2};})()`);
  await cdp("Input.dispatchMouseEvent", { type: "mousePressed", ...point, button: "left", clickCount: 1 });
  await cdp("Input.dispatchMouseEvent", { type: "mouseReleased", ...point, button: "left", clickCount: 1 });
}
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Emulation.setFocusEmulationEnabled", { enabled: true });
  await cdp("Emulation.setDeviceMetricsOverride", { width: 375, height: 812, deviceScaleFactor: 1, mobile: true });
  await cdp("Page.navigate", { url: origin });
  await waitFor("document.readyState === 'complete' && document.querySelectorAll('.char-card').length === 4");
  await evaluate(`(async () => {
    window.examples = await fetchJson('/037-fixtures');
    window.show = session => { state.combatBusy=false; state.combatIntroSeenId=session.combat.id;
      els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(structuredClone(session)); };
    window.visibleLogs = () => [...els.combatLog.children].filter(n=>getComputedStyle(n).display!=='none');
    window.rect = selector => document.querySelector(selector).getBoundingClientRect();
    window.domResult = () => ({logs:[...els.combatLog.children].map(n=>n.textContent),
      bars:[...els.combatScreen.querySelectorAll('.combat-resource')].map(n=>[n.querySelector('strong').textContent,n.querySelector('b').style.width]),
      enemies:[...els.combatEnemies.children].map(n=>[n.dataset.combatTarget,n.className,n.disabled])});
  })()`);
  for (const name of ["normal", "draco"]) {
    await evaluate(`show(examples.${name}); document.querySelector('.combat-arena').scrollTop=0`);
    await evaluate("Promise.all([...document.images].filter(i=>i.getAttribute('src')).map(i=>i.decode().catch(()=>{})))");
    check(await evaluate("innerWidth===375 && innerHeight===812"), `${name}: 375x812 viewport`);
    check(await evaluate("rect('#combatEnemies').bottom <= rect('.player-combatant').top && Math.abs(rect('#combatEnemies').width-rect('.combat-arena').width)<2"), `${name}: enemies first and full width`);
    check(await evaluate("[...els.combatEnemies.querySelectorAll('img')].every(i=>i.getBoundingClientRect().height>=innerHeight*.28-1)"), `${name}: portraits at least 28vh`);
    check(await evaluate("rect('#combatPlayerImage').width===40 && rect('#combatPlayerImage').height===40 && rect('.player-combatant').height<64"), `${name}: 40px avatar and compact player row`);
    check(await evaluate("[...document.querySelectorAll('.player-combatant .combat-resource strong')].every(n=>n.scrollWidth<=n.clientWidth)"), `${name}: resource values fit the compact row`);
    check(await evaluate("visibleLogs().length===3 && els.combatLogToggle.getAttribute('aria-expanded')==='false'"), `${name}: latest three log entries by default`);
    check(await evaluate("[...els.combatActionTabs.children].every(n=>Math.abs(n.getBoundingClientRect().top-els.combatActionTabs.firstElementChild.getBoundingClientRect().top)<1)"), `${name}: tabs stay on one row`);
    check(await evaluate("getComputedStyle(els.combatActions).gridTemplateColumns.split(' ').length===2 && rect('.combat-command-deck').bottom<=812 && rect('.combat-command-deck').bottom>780"), `${name}: two columns at viewport bottom`);
    check(await evaluate("document.documentElement.scrollWidth<=innerWidth && document.querySelector('.combat-arena').scrollWidth<=document.querySelector('.combat-arena').clientWidth"), `${name}: no horizontal overflow`);
    await delay(150);
    await screenshot(name);
  }
  await click("#combatLogToggle");
  check(await evaluate("els.combatLogToggle.getAttribute('aria-expanded')==='true' && visibleLogs().length===state.session.combat.log.length"), "tap expands every log entry");
  check(await evaluate("rect('#combatLog').height>120 && els.combatLog.children.length>3"), "expanded log has room for more than three lines");
  await screenshot("log-expanded");
  await evaluate("renderCombat(state.session)");
  check(await evaluate("state.combatLogExpanded"), "same-battle updates preserve expanded state");
  await evaluate("els.combatLogToggle.focus()");
  await cdp("Input.dispatchKeyEvent", { type: "keyDown", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13, text: "\r" });
  await cdp("Input.dispatchKeyEvent", { type: "keyUp", key: "Enter", code: "Enter", windowsVirtualKeyCode: 13 });
  check(await evaluate("!state.combatLogExpanded && visibleLogs().length===3"), "keyboard collapses log");
  await click("#combatLogToggle");
  await evaluate("show(examples.normal)");
  check(await evaluate("!state.combatLogExpanded"), "new battle resets to collapsed log");
  for (const reduced of [false, true]) {
    await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: reduced ? "reduce" : "no-preference" }] });
    for (const name of ["normal", "phase", "heal", "knockout"]) {
      await evaluate(`show(examples.effects.${name}.after); window.expected=domResult(); show(examples.effects.${name}.before);
        window.fxSeen=false; window.motionSeen=false; window.observer=new MutationObserver(()=>{
          if(document.querySelector('#combatFxLayer').children.length) window.fxSeen=true;
          if(document.querySelector('.combat-impact,.combat-phase-flash,.combat-delay-bar')) window.motionSeen=true;
        });
        observer.observe(document.body,{childList:true,subtree:true});
        window.done=false; playCombatEvents(examples.effects.${name}.before,examples.effects.${name}.after).then(()=>{renderSession(structuredClone(examples.effects.${name}.after));window.done=true;}); void 0`);
      await waitFor("window.done");
      check(await evaluate("JSON.stringify(domResult())===JSON.stringify(window.expected)"), `${name}/${reduced}: playback settles to engine state`);
      check(await evaluate(reduced ? "!window.motionSeen" : "window.fxSeen"), `${name}/${reduced}: motion preference respected`);
      await evaluate("observer.disconnect()");
    }
  }
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
  await evaluate("show(examples.draco)");
  check(await evaluate("getComputedStyle(els.combatLogToggle).display==='none' && visibleLogs().length===state.session.combat.log.length"), "desktop keeps full log without toggle");
  check(errors.length===0, "no browser exceptions");
  console.log(`${checks.length} browser checks passed`);
} catch (error) {
  await screenshot("failure");
  errors.push(String(error));
  console.error(error);
  process.exitCode=1;
} finally {
  await writeFile(join(output,"checks.json"),JSON.stringify({width:375,height:812,checks,errors},null,2)+"\n");
  ws.send(JSON.stringify({id:++sequence,method:"Browser.close"}));
  ws.close();
}
