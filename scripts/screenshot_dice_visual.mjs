import { writeFile } from "node:fs/promises";
import { join } from "node:path";

const [port, origin, output] = process.argv.slice(2);
const pages = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
const ws = new WebSocket(pages.find(page => page.type === "page").webSocketDebuggerUrl);
await new Promise(resolve => ws.addEventListener("open", resolve, { once: true }));
let sequence = 0;
const pending = new Map(), errors = [], checks = [];
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
async function check(expression, label) {
  if (!await evaluate(expression)) throw new Error(label);
  checks.push(label);
}
async function waitFor(expression) {
  for (let attempt = 0; attempt < 200; attempt++) {
    if (await evaluate(expression)) return;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  throw new Error(`Timeout: ${expression}`);
}
async function capture(name) {
  const screenshot = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  await writeFile(join(output, `${name}.png`), Buffer.from(screenshot.data, "base64"));
}
async function freeze(time) {
  await evaluate(`els.diceCheckCard.getAnimations({subtree:true}).forEach(a=>{a.pause();a.currentTime=${time};})`);
}
const preview = { dice: "1d20", attribute_label: "敏捷", skill: "隠密", modifier: 5, dc: 10,
  proficiency_bonus: 2, advantage: "advantage", advantage_reasons: ["ロビンの助言"] };
function roll(faces, index, enabled = true) {
  return { expression: "1d20+dex", rolls: faces, selected_index: index, selected_roll: faces[index],
    advantage: faces.length === 2 ? (faces[index] === Math.min(...faces) ? "disadvantage" : "advantage") : null,
    attr_mod: 5, total: faces[index] + 5, dc: 10,
    critical_enabled: enabled, success: faces[index] + 5 >= 10,
    outcome: enabled && faces[index] === 1 ? "critical_failure" : "success" };
}
async function start(checkData = preview) {
  await evaluate(`closeDiceCheck(); startDicePresentation(${JSON.stringify(checkData)}, "裏口から忍び込む")`);
}
async function result(value) {
  await evaluate(`stopDiceRollAnimation(); showDiceFaces(${JSON.stringify(value)});
    showDiceCalculation(${JSON.stringify(value)}); showDiceOutcome(${JSON.stringify(value)})`);
  await freeze(400);
}
try {
  await cdp("Page.enable");
  await cdp("Runtime.enable");
  await cdp("Page.navigate", { url: origin });
  await waitFor("document.querySelectorAll('.char-card').length === 4 && document.readyState === 'complete'");
  await evaluate(`(async()=>{
    const session = await fetchJson('/fixture?location=castle_town');
    els.startScreen.style.display='none'; els.gameScreen.style.display=''; renderSession(session);
    await Promise.all(['bone','bone_cracked','ruby','ruby_cracked','iron','iron_cracked','tray'].map(async name=>{
      const image = new Image(); image.src='/static/images/dice_'+name+'.webp'; await image.decode();
    }));
  })()`);
  for (const mobile of [false, true]) {
    const suffix = mobile ? "-mobile" : "";
    await cdp("Emulation.setDeviceMetricsOverride", { width: mobile ? 390 : 1280, height: mobile ? 844 : 800, deviceScaleFactor: 1, mobile });
    await start();
    await freeze(60);
    await check("Number(getComputedStyle(document.querySelector('.dice-check-dice'),'::before').opacity)>0 && getComputedStyle(document.querySelector('.dice-flight')).opacity==='0'", `${suffix}: tray appears before the falling dice`);
    const samples = [];
    for (const time of [240, 348, 438, 510, 600]) {
      await freeze(time);
      samples.push(await evaluate(`({height: new DOMMatrix(getComputedStyle(document.querySelector('.dice-flight')).transform).m42,
        shadow: Number(getComputedStyle(document.querySelector('.dice-shadow')).opacity)})`));
    }
    if (!(samples[0].height === 0 && samples[1].height < samples[3].height && samples[3].height < 0
        && samples[2].height === 0 && samples[4].height === 0 && samples[1].shadow < samples[0].shadow)) {
      throw new Error(`Bounce or shadow mismatch: ${JSON.stringify(samples)}`);
    }
    checks.push(`${suffix}: two diminishing bounces with a lighter airborne shadow`);
    await freeze(350);
    await check("getComputedStyle(document.querySelector('.dice-check-dice'),'::before').backgroundImage.includes('dice_tray.webp')", `${suffix}: painted tray loaded`);
    await check("els.diceNatural.hidden && els.diceNaturalSecond.hidden", `${suffix}: no tumbling digits`);
    await check("document.querySelector('.dice-body').getAnimations().some(a=>a.animationName==='d20SpinDown')", `${suffix}: painted die spins with CSS`);
    await capture(`falling${suffix}`);
    await freeze(5000);
    await check("els.diceCheckCard.classList.contains('rolling') && !els.diceCheckCard.classList.contains('settling')", `${suffix}: waiting never settles`);
    await check("document.querySelector('.dice-body').getAnimations().some(a=>a.animationName==='d20Tumble' && a.effect.getTiming().iterations===Infinity)", `${suffix}: waiting loop is unbounded`);
    await evaluate("window.motionBeforeSettle=getComputedStyle(els.diceFirst.querySelector('.dice-body')).transform; settleDice()");
    await check("els.diceFirst.style.getPropertyValue('--dice-settle-transform') === window.motionBeforeSettle", `${suffix}: settle starts at the current rotation`);
    await result(roll([3, 17], 1));
    await check("getComputedStyle(els.diceFirst).opacity === '0.3' && getComputedStyle(els.diceFirst).transform !== 'none' && getComputedStyle(els.diceSecond).opacity === '1'", `${suffix}: discarded die dims and shrinks`);
    await check("els.diceFirst.getBoundingClientRect().right < els.diceSecond.getBoundingClientRect().left", `${suffix}: two distinct landing positions`);
    await check("document.documentElement.scrollWidth <= innerWidth && els.diceCheckCard.scrollWidth <= els.diceCheckCard.clientWidth", `${suffix}: no horizontal overflow`);
    await capture(`result${suffix}`);
    await start();
    await result(roll([1, 20], 1));
    await check("getComputedStyle(els.diceSecond,'::after').animationName === 'd20Halo' && getComputedStyle(els.diceFirst,'::after').content === 'none'", `${suffix}: only selected natural 20 glows`);
    await capture(`critical-success${suffix}`);
    await start({...preview, advantage: "disadvantage", advantage_reasons: ["傷が痛む"]});
    await result(roll([12, 1], 1));
    await check("getComputedStyle(els.diceSecond.querySelector('.dice-body'),'::after').opacity === '1' && getComputedStyle(els.diceFirst.querySelector('.dice-body'),'::after').opacity === '0'", `${suffix}: only selected natural 1 cracks`);
    await capture(`critical-failure${suffix}`);
    await start();
    await result(roll([1, 20], 1, false));
    await check("!els.diceCheckCard.classList.contains('critical-success') && !els.diceCheckCard.classList.contains('critical-failure') && els.diceCritical.hidden", `${suffix}: disabled extremes have no effects`);
  }
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-reduced-motion", value: "reduce" }] });
  await start({...preview, advantage: "disadvantage", advantage_reasons: ["傷が痛む"]});
  await result(roll([12, 1], 1));
  await check("els.diceCheckCard.getAnimations({subtree:true}).length===0", "reduced motion disables tray, dice, numbers and critical animations");
  await capture("reduced-motion-mobile");
  await cdp("Emulation.setEmulatedMedia", { features: [] });

  // Contact sheet uses the shipped CSS number treatment, alongside untouched PNG candidates.
  await cdp("Emulation.setDeviceMetricsOverride", { width: 1200, height: 1160, deviceScaleFactor: 1, mobile: false });
  await evaluate(`(() => {
    closeDiceCheck();
    const labels=['A 旧象牙／骨','B 深紅の宝石','C 黒鉄'];
    const materials=['bone','ruby','iron'];
    const sheet=document.createElement('main'); sheet.id='diceSheet';
    sheet.style.cssText='position:fixed;inset:0;z-index:10000;padding:24px;background:var(--panel);display:grid;grid-template-columns:repeat(3,1fr);gap:16px;color:var(--text)';
    materials.forEach((material,index)=>{
      const section=document.createElement('section');
      section.className='dice-check-card instant-result'; section.dataset.diceMaterial=material;
      section.style.cssText='width:100%;max-height:none;overflow:visible;box-shadow:none;padding:16px';
      section.innerHTML='<h2>'+labels[index]+'</h2>';
      ['01','02','cracked'].forEach(variant=>{
        const figure=document.createElement('figure'); figure.style.margin='12px 0';
        const img=document.createElement('img'); img.src='/042-candidates/dice_'+material+'_'+variant+'.png';
        img.style.cssText='width:190px;height:190px;display:block;margin:auto';
        const label=document.createElement('figcaption'); label.textContent=variant==='cracked'?'ひび割れ':'候補 '+variant;
        figure.append(img,label); section.append(figure);
      });
      const sample=document.createElement('div'); sample.className='dice-d20 faces-visible';
      sample.style.cssText='--dice-size:160px;margin:18px auto 8px';
      sample.innerHTML='<div class="dice-body"><span class="dice-number" style="font-size:41px">17</span></div>';
      section.append(sample);
      const caption=document.createElement('p'); caption.textContent='候補 01 ＋ 17'; section.append(caption);
      sheet.append(section);
    });
    const tray=document.createElement('img'); tray.src='/static/images/dice_tray.webp';
    tray.style.cssText='grid-column:1/-1;width:320px;height:160px;justify-self:center'; sheet.append(tray);
    document.body.append(sheet);
  })()`);
  await evaluate("Promise.all([...document.querySelectorAll('#diceSheet img')].map(i=>i.decode()))");
  await check("[...document.querySelectorAll('#diceSheet .dice-number')].every(e=>e.textContent==='17' && getComputedStyle(e).fontFamily.includes('Georgia'))", "sheet overlays real serif numbers on all three materials");
  await capture("dice-sheet");
  if (errors.length) throw new Error(JSON.stringify(errors));
  console.log(`${checks.length} browser checks passed; 9 screenshots and dice-sheet.png`);
} catch (error) {
  await capture("failure");
  console.error(error);
  process.exitCode = 1;
} finally {
  await writeFile(join(output, "checks.json"), JSON.stringify({ ok: !process.exitCode, checks, browserErrors: errors }, null, 2) + "\n");
  ws.send(JSON.stringify({ id: ++sequence, method: "Browser.close" }));
  ws.close();
}
