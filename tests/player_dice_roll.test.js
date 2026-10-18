const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const { test } = require("node:test");

// Exercise the shipped client with an offline DOM and a controllable clock/request queue.
function client({ reducedMotion = false } = {}) {
  let now = 0, nextTimer = 0;
  const timers = new Map(), nodes = new Map(), requests = [], rendered = [], messages = [];
  class Element {
    constructor() {
      this.style = { setProperty(name, value) { this[name] = value; } };
      this.dataset = {};
      this.attributes = {};
      this.listeners = {};
      this.children = [];
      this.textContent = "";
      this.innerHTML = "";
      this.value = "";
      this.hidden = false;
      this.parentElement = this;
      const classes = new Set();
      this.classList = {
        add: (...names) => names.forEach(name => classes.add(name)),
        remove: (...names) => names.forEach(name => classes.delete(name)),
        contains: name => classes.has(name),
        toggle: (name, on = !classes.has(name)) => on ? classes.add(name) : classes.delete(name),
      };
    }
    addEventListener(type, handler, capture = false) { (this.listeners[type] ||= []).push({ handler, capture }); }
    setAttribute(name, value) { this.attributes[name] = String(value); }
    getAttribute(name) { return this.attributes[name]; }
    querySelector() { return this.children[0] || null; }
    querySelectorAll() { return this.children; }
    contains(node) { return node === this || this.children.some(child => child.contains(node)); }
    closest() { return this; }
    append(...children) { this.children.push(...children); }
    appendChild(child) { this.append(child); }
    focus() { document.activeElement = this; }
  }
  const document = new Element();
  document.querySelector = selector => {
    if (!nodes.has(selector)) nodes.set(selector, new Element());
    return nodes.get(selector);
  };
  document.querySelectorAll = () => [];
  document.createElement = () => new Element();
  const schedule = (fn, ms, interval = false) => {
    const id = ++nextTimer;
    timers.set(id, { fn, at: now + ms, interval: interval ? ms : 0 });
    return id;
  };
  const context = vm.createContext({
    document, console, URLSearchParams,
    performance: { now: () => now },
    window: {
      setTimeout: (fn, ms) => schedule(fn, ms), clearTimeout: id => timers.delete(id),
      setInterval: (fn, ms) => schedule(fn, ms, true), clearInterval: id => timers.delete(id),
      matchMedia: () => ({ matches: reducedMotion }), location: { search: "" },
      getComputedStyle: () => ({ transform: "matrix(0, 1, -1, 0, 0, -4)", opacity: "0.4" }),
    },
    fetch: (url, options) => new Promise((resolve, reject) => requests.push({ url, options, resolve, reject })),
    rendered, messages,
  });
  const source = fs.readFileSync("client/app.js", "utf8").replace(/\ninit\(\);\r?\n/, "\n");
  vm.runInContext(source + `
    choiceDebug = () => {};
    choiceLayoutDebug = () => ({});
    rubyHtml = text => String(text);
    restoreChoicePortrait = portrait => { state.choicePortrait = portrait; };
    renderChoices = () => { els.choicesArea.style.display = ""; };
    addMessage = (role, speaker, text) => messages.push({role, speaker, text});
    renderSession = session => { state.session = session; rendered.push(session); renderLatestDiceResult(session.dice_log); };
    globalThis.api = {state, els, openDiceCheck, cancelDiceCheck, confirmDiceCheck,
      submitTurn, submitChoice, handleChoiceListClick, renderTurnResponse, skipDicePresentation};
  `, context);
  const { state, els } = context.api;
  state.sessionId = "local";
  state.session = { id: "local", dice_log: [], in_combat: false };
  const choice = { id: "cross_lava_bridge", text: "溶岩の橋を渡る", check: {
    dice: "1d20", attribute: "dex", attribute_label: "敏捷", modifier: 5, dc: 14,
  } };
  state.pendingChoices = [choice];
  state.choicesRevealed = true;
  els.diceCheckCard.style.display = "none";
  const card = new Element();
  card.dataset = { choiceIndex: "0", choiceText: choice.text, actionId: choice.id };
  els.choicesList.append(card);
  els.diceCheckCard.append(els.diceCheckRoll, els.diceCheckCancel);
  async function flush() { for (let i = 0; i < 20; i++) await Promise.resolve(); }
  async function tick(milliseconds) {
    const end = now + milliseconds;
    await flush();
    while (true) {
      const next = [...timers].filter(([, timer]) => timer.at <= end).sort((a, b) => a[1].at - b[1].at)[0];
      if (!next) break;
      const [id, timer] = next;
      now = timer.at;
      if (timer.interval) timer.at += timer.interval;
      else timers.delete(id);
      timer.fn();
      await flush();
    }
    now = end;
    await flush();
  }
  function event(type, extra = {}) {
    const e = { target: els.diceCheckCard, preventDefault() { this.prevented = true; },
      stopImmediatePropagation() { this.stopped = true; }, ...extra };
    for (const { handler } of document.listeners[type] || []) {
      handler(e);
      if (e.stopped) break;
    }
    return e;
  }
  function response(natural = 14, extra = {}) {
    return { id: "local", in_combat: false, dice_log: [{
      expression: "1d20+dex", rolls: [natural], attr_mod: 5, total: natural + 5, dc: 14,
      success: natural + 5 >= 14, critical_success: natural === 20, critical_failure: natural === 1,
      created_at: "2026-10-19T00:00:00Z",
    }], ...extra };
  }
  function answer(session = response()) { requests.at(-1).resolve({ ok: true, json: async () => session }); }
  return { ...context.api, document, choice, card, requests, rendered, messages, timers, tick, flush, event, response, answer };
}

test("selecting a check waits for confirmation; cancel preserves the submenu and focus", () => {
  const c = client();
  const stack = [{ choices: [], portrait: null }];
  c.state.choiceStack = stack;
  c.handleChoiceListClick({ target: c.card });
  assert.equal(c.requests.length, 0);
  assert.equal(c.els.diceCheckTitle.innerHTML, c.choice.text);
  assert.equal(c.els.diceCheckSummary.textContent, "敏捷判定　DC 14");
  assert.equal(c.els.diceCheckFormula.textContent, "1d20 ＋ 5（敏捷）");
  assert.equal(c.document.activeElement, c.els.diceCheckRoll);
  c.event("keydown", { key: "Tab" });
  assert.equal(c.document.activeElement, c.els.diceCheckCancel);
  c.event("keydown", { key: "Escape" });
  assert.equal(c.requests.length, 0);
  assert.equal(c.state.pendingChoices[0], c.choice);
  assert.equal(c.state.choiceStack, stack);
  assert.equal(c.els.choicesArea.style.display, "");
  assert.equal(c.els.diceCheckCard.style.display, "none");
  assert.equal(c.document.activeElement, c.card);
});

test("Enter and Space submit exactly one server-only roll request", async () => {
  for (const key of ["Enter", " "]) {
    const c = client();
    c.openDiceCheck(c.choice, c.card);
    c.event("keydown", { key });
    c.confirmDiceCheck();
    assert.equal(c.requests.length, 1);
    assert.deepEqual(JSON.parse(c.requests[0].options.body), { text: c.choice.text, action_id: c.choice.id });
    assert.equal(c.state.turnBusy, true);
    await c.tick(1500);
    assert.equal(c.els.diceCheckCard.classList.contains("rolling"), true);
    assert.equal(c.rendered.length, 0);
    c.answer();
    await c.flush();
    assert.equal(c.els.diceCheckCard.classList.contains("settling"), true);
    assert.equal(c.els.diceNatural.hidden, true);
    await c.tick(120);
    assert.equal(c.els.diceNatural.textContent, "14");
    await c.tick(1480);
    assert.equal(c.rendered.length, 1);
    assert.equal(c.state.turnBusy, false);
    assert.equal(c.timers.size, 0);
  }
});

test("900ms roll, 120ms settle and 80ms fade preserve the original total duration", async () => {
  const c = client();
  c.openDiceCheck(c.choice, c.card);
  const done = c.confirmDiceCheck();
  c.answer();
  await c.tick(899);
  assert.equal(c.els.diceCheckCard.classList.contains("rolling"), true);
  assert.equal(c.rendered.length, 0);
  await c.tick(1);
  assert.equal(c.els.diceCheckCard.classList.contains("rolling"), false);
  assert.equal(c.els.diceCheckCard.classList.contains("settling"), true);
  assert.equal(c.els.diceNatural.hidden, true);
  assert.equal(c.els.diceCheckCard.style["--dice-settle-duration"], "120ms");
  assert.equal(c.els.diceCheckCard.style["--dice-number-duration"], "80ms");
  assert.equal(c.els.diceFirst.style["--dice-settle-transform"], "matrix(0, 1, -1, 0, 0, -4)");
  assert.equal(c.els.diceFirst.style["--dice-settle-shadow-opacity"], "0.4");
  await c.tick(119);
  assert.equal(c.els.diceNatural.hidden, true);
  await c.tick(1);
  assert.equal(c.els.diceNatural.textContent, "14");
  assert.equal(c.els.diceNatural.hidden, false);
  assert.equal(c.els.diceCheckCard.classList.contains("settling"), false);
  assert.equal(c.els.diceCheckCard.classList.contains("faces-visible"), true);
  assert.equal(c.els.diceCalculation.hidden, true);
  await c.tick(79);
  assert.equal(c.els.diceCalculation.hidden, true);
  await c.tick(1);
  assert.equal(c.els.diceCalculation.textContent, "＋5 ＝ 19");
  assert.equal(c.els.diceOutcome.textContent, "");
  await c.tick(200);
  assert.equal(c.els.diceOutcome.textContent, "DC 14　成功");
  await c.tick(1199);
  assert.equal(c.rendered.length, 0);
  await c.tick(1);
  await done;
  assert.equal(c.rendered.length, 1);
  assert.equal(c.els.diceCheckCard.style.display, "none");
  assert.equal(c.els.diceRollFace.textContent, "19");
  assert.match(c.els.diceBannerText.textContent, /14 \+5 = 19/);
});

test("free input starts its 600ms animation only after the server response", async () => {
  const c = client();
  c.els.input.value = "溶岩の橋を渡る";
  const done = c.submitTurn({ preventDefault() {} });
  assert.equal(c.state.dicePresentation, null);
  assert.deepEqual(JSON.parse(c.requests[0].options.body), { text: "溶岩の橋を渡る" });
  c.answer();
  await c.tick(599);
  assert.equal(c.els.diceCheckCard.classList.contains("rolling"), true);
  await c.tick(1);
  assert.equal(c.els.diceCheckCard.classList.contains("settling"), true);
  assert.equal(c.els.diceNatural.hidden, true);
  await c.tick(120);
  assert.equal(c.els.diceNatural.textContent, "14");
  await c.tick(1480);
  await done;
  assert.equal(c.rendered.length, 1);
});

test("attribute-free checks show zero modifier and a normal failure without a critical effect", async () => {
  const c = client({ reducedMotion: true });
  c.choice.check = { dice: "1d20", attribute: "", attribute_label: "", modifier: 0, dc: 14 };
  c.openDiceCheck(c.choice, c.card);
  assert.equal(c.els.diceCheckSummary.textContent, "判定　DC 14");
  assert.equal(c.els.diceCheckFormula.textContent, "1d20 ＋ 0");
  const done = c.confirmDiceCheck();
  const session = c.response(7);
  session.dice_log[0].expression = "1d20";
  session.dice_log[0].total = 7;
  delete session.dice_log[0].attr_mod;
  c.answer(session);
  await c.flush();
  assert.equal(c.els.diceCalculation.textContent, "＋0 ＝ 7");
  assert.equal(c.els.diceOutcome.textContent, "DC 14　失敗");
  assert.equal(c.els.diceCritical.hidden, true);
  await c.tick(1200);
  await done;
  assert.equal(c.els.diceBanner.classList.contains("failure"), true);
  await c.renderTurnResponse(session);
  assert.equal(c.els.diceBanner.style.display, "");
});

test("skip before a response never fabricates a final number or clicks through", async () => {
  const c = client();
  c.openDiceCheck(c.choice, c.card);
  const done = c.confirmDiceCheck();
  const click = c.event("click", { target: c.els.newSessionButton });
  assert.equal(click.stopped, true);
  assert.equal(c.els.diceNatural.textContent, "?");
  assert.equal(c.timers.size, 0);
  c.answer();
  await c.flush();
  assert.equal(c.els.diceNatural.textContent, "14");
  assert.equal(c.els.diceCalculation.hidden, false);
  assert.equal(c.els.diceOutcome.textContent, "DC 14　成功");
  await c.tick(1200);
  await done;
});

test("skip reveals an available result immediately; a second click dismisses it", async () => {
  const c = client();
  const done = c.renderTurnResponse(c.response());
  await c.tick(50);
  c.event("click");
  await c.flush();
  assert.equal(c.els.diceNatural.textContent, "14");
  assert.equal(c.els.diceOutcome.textContent, "DC 14　成功");
  assert.equal(c.rendered.length, 0);
  c.event("click");
  await done;
  assert.equal(c.rendered.length, 1);
  assert.equal(c.timers.size, 0);
});

test("natural 20 and 1 use the critical effects and labels, never the modified total", async () => {
  for (const [natural, label, effect] of [[20, "大成功", "critical-success"], [1, "大失敗", "critical-failure"]]) {
    const c = client({ reducedMotion: true });
    const done = c.renderTurnResponse(c.response(natural));
    await c.flush();
    assert.equal(c.els.diceNatural.textContent, String(natural));
    assert.equal(c.els.diceCritical.textContent, label);
    assert.equal(c.els.diceCheckCard.classList.contains(effect), true);
    assert.equal(c.els.diceCheckCard.classList.contains("rolling"), false);
    await c.tick(1200);
    await done;
  }
});

test("reduced motion shows the result immediately after the response, with no rolling interval", async () => {
  const c = client({ reducedMotion: true });
  c.openDiceCheck(c.choice, c.card);
  const done = c.confirmDiceCheck();
  assert.equal(c.timers.size, 0);
  c.answer();
  await c.flush();
  assert.equal(c.els.diceNatural.textContent, "14");
  assert.equal(c.els.diceCalculation.textContent, "＋5 ＝ 19");
  assert.equal(c.els.diceOutcome.textContent, "DC 14　成功");
  await c.tick(1200);
  await done;
});

test("success line follows the engine outcome even when natural extremes are disabled", async () => {
  const c = client({ reducedMotion: true });
  const session = c.response(1);
  session.dice_log[0].dc = 5;
  session.dice_log[0].success = true;
  session.dice_log[0].outcome = "success";
  session.dice_log[0].critical_enabled = false;
  const done = c.renderTurnResponse(session);
  await c.flush();
  assert.equal(c.els.diceOutcome.textContent, "DC 5　成功");
  assert.equal(c.els.diceCritical.textContent, "");
  assert.equal(c.els.diceCritical.hidden, true);
  assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), false);
  assert.equal(c.els.diceOutcome.classList.contains("success"), true);
  await c.tick(1200);
  await done;
  assert.equal(c.els.diceBanner.classList.contains("success"), true);
});

test("HTTP, network and malformed responses close the animation and restore clickable nested choices", async () => {
  for (const failure of ["http", "network", "json"]) {
    const c = client();
    const stack = [{ choices: [], portrait: null }];
    c.state.choiceStack = stack;
    c.state.choicePortrait = "npc.png";
    c.openDiceCheck(c.choice, c.card);
    const done = c.confirmDiceCheck();
    if (failure === "network") c.requests[0].reject(new Error("接続エラー"));
    else c.requests[0].resolve({ ok: failure !== "http", text: async () => "接続エラー",
      json: async () => { throw new Error("接続エラー"); } });
    await done;
    assert.equal(c.els.diceCheckCard.style.display, "none");
    assert.equal(c.els.choicesArea.style.display, "");
    assert.equal(c.state.turnBusy, false);
    assert.equal(c.state.choiceStack, stack);
    assert.equal(c.state.choicePortrait, "npc.png");
    assert.equal(c.state.pendingChoices[0], c.choice);
    assert.match(c.messages.at(-1).text, /エラー/);
    assert.equal(c.timers.size, 0);
    c.openDiceCheck(c.choice, c.card);
    assert.equal(c.state.pendingCheck.choice, c.choice);
  }
});

test("no new roll, DC999 and entering combat bypass the animation and clean up any pending spin", async () => {
  for (const mode of ["no-roll", "dc999", "combat", "already-combat"]) {
    const c = client();
    const session = c.response();
    if (mode === "no-roll") session.dice_log = [];
    if (mode === "dc999") session.dice_log[0].dc = 999;
    if (mode === "combat") session.in_combat = true;
    if (mode === "already-combat") c.state.session.in_combat = true;
    c.openDiceCheck(c.choice, c.card);
    if (mode === "already-combat") assert.equal(c.state.pendingCheck, null);
    const done = mode === "already-combat" ? c.submitChoice(c.choice.text, c.choice.id) : c.confirmDiceCheck();
    c.answer(session);
    await done;
    assert.equal(c.rendered.length, 1);
    assert.equal(c.els.diceCheckCard.style.display, "none");
    assert.equal(c.timers.size, 0);
  }
});

test("repeated session data does not replay a roll, but a new identical roll does", async () => {
  const c = client({ reducedMotion: true });
  const session = c.response();
  c.state.session = session;
  await c.renderTurnResponse(session);
  assert.equal(c.timers.size, 0);
  const next = c.response();
  next.dice_log[0].created_at = "2026-10-19T00:00:01Z";
  const done = c.renderTurnResponse(next);
  await c.flush();
  assert.equal(c.els.diceCheckCard.style.display, "");
  await c.tick(1200);
  await done;
});

test("skill and proficiency labels accompany both dice and their selected result", async () => {
  for (const [mode, faces, selected, index, reason] of [
    ["advantage", [3, 14], 14, 1, "ロビンの助言"],
    ["disadvantage", [3, 20], 3, 0, "傷が痛む"],
  ]) {
    const c = client({ reducedMotion: true });
    Object.assign(c.choice.check, { skill: "隠密", proficiency_bonus: 2, dc: 10,
      advantage: mode, advantage_reasons: [reason] });
    c.openDiceCheck(c.choice, c.card);
    assert.equal(c.els.diceCheckSummary.textContent, "隠密（敏捷）判定　DC 10");
    assert.equal(c.els.diceCheckFormula.textContent, "1d20 ＋ 5（敏捷＋熟練）");
    assert.equal(c.els.diceCheckAdvantage.textContent, `${mode === "advantage" ? "有利" : "不利"}：${reason}`);
    const done = c.confirmDiceCheck();
    const session = c.response(selected);
    Object.assign(session.dice_log[0], { rolls: faces, selected_roll: selected, selected_index: index,
      advantage: mode, advantage_reasons: [reason] });
    c.answer(session);
    await c.flush();
    assert.equal(c.els.diceNatural.textContent, String(faces[0]));
    assert.equal(c.els.diceNaturalSecond.textContent, String(faces[1]));
    assert.equal(c.els.diceSecond.hidden, false);
    assert.equal(c.els.diceFirst.classList.contains("selected"), index === 0);
    assert.equal(c.els.diceSecond.classList.contains("selected"), index === 1);
    assert.equal(c.els.diceFirst.classList.contains("discarded"), index === 1);
    assert.equal(c.els.diceSecond.classList.contains("discarded"), index === 0);
    assert.equal(c.els.diceCritical.hidden, true);
    assert.equal(c.els.diceOutcome.classList.contains(selected === 14 ? "success" : "failure"), true);
    await c.tick(1200);
    await done;
    assert.match(c.els.diceBannerText.textContent, new RegExp(`\\[${faces.join(", ")}\\] → ${selected}`));
  }
});

test("free observation animates both dice for 600ms and uses the selected extreme", async () => {
  const c = client();
  const session = c.response(20);
  Object.assign(session.dice_log[0], { rolls: [1, 20], selected_roll: 20, selected_index: 1,
    advantage: "advantage", advantage_reasons: ["ロビンの助言"] });
  const done = c.renderTurnResponse(session);
  await c.tick(599);
  assert.equal(c.els.diceSecond.hidden, false);
  assert.equal(c.els.diceCheckActions.hidden, true);
  assert.equal(c.els.diceCheckCard.classList.contains("rolling"), true);
  await c.tick(401);
  assert.equal(c.els.diceCritical.textContent, "大成功");
  assert.equal(c.els.diceSecond.classList.contains("selected"), true);
  await c.tick(1200);
  await done;
});

test("cancelled advantage uses one die and resets the previous pair's highlight", async () => {
  const c = client({ reducedMotion: true });
  c.els.diceSecond.hidden = false;
  c.els.diceFirst.classList.add("discarded");
  c.choice.check.advantage = null;
  c.choice.check.advantage_reasons = ["ロビンの助言", "傷が痛む"];
  c.openDiceCheck(c.choice, c.card);
  assert.equal(c.els.diceSecond.hidden, true);
  assert.equal(c.els.diceFirst.classList.contains("discarded"), false);
  assert.equal(c.els.diceCheckAdvantage.hidden, true);
  c.cancelDiceCheck();
});

test("disabled extremes show only their points and the engine outcome", async () => {
  for (const natural of [1, 20]) {
    const c = client({ reducedMotion: true });
    const session = c.response(natural);
    Object.assign(session.dice_log[0], { critical_enabled: false, outcome: "failure", success: false });
    const done = c.renderTurnResponse(session);
    await c.flush();
    assert.equal(c.els.diceNatural.textContent, String(natural));
    assert.equal(c.els.diceCritical.hidden, true);
    assert.equal(c.els.diceCheckCard.classList.contains("critical-success"), false);
    assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), false);
    assert.equal(c.els.diceOutcome.textContent, "DC 14　失敗");
    assert.equal(c.els.diceOutcome.classList.contains("failure"), true);
    await c.tick(1200);
    await done;
    assert.doesNotMatch(c.els.diceBannerText.textContent, /大成功|大失敗/);
  }
});

test("crucial previews show the server risk and clear it for the next ordinary check", () => {
  const c = client();
  for (const [reason, label] of [["combat", "失敗すると戦闘"], ["game_over", "失敗すると危険"]]) {
    Object.assign(c.choice.check, { crucial: true, crucial_reason: reason });
    c.openDiceCheck(c.choice, c.card);
    assert.equal(c.els.diceCheckCrucial.textContent, label);
    assert.equal(c.els.diceCheckCrucial.hidden, false);
    c.cancelDiceCheck();
  }
  delete c.choice.check.crucial;
  c.openDiceCheck(c.choice, c.card);
  assert.equal(c.els.diceCheckCrucial.hidden, true);
  assert.equal(c.els.diceCheckCrucial.textContent, "");
});

test("ordinary crucial failures finish the original presentation before combat or an ending", async () => {
  for (const reason of ["combat", "game_over"]) {
    const c = client();
    Object.assign(c.choice.check, { crucial: true, crucial_reason: reason });
    c.openDiceCheck(c.choice, c.card);
    const done = c.confirmDiceCheck();
    const session = c.response(7, { in_combat: reason === "combat",
      game_over: reason === "game_over" ? { reason: "物語はここで終わりました。" } : null });
    Object.assign(session.dice_log[0], { crucial: true, crucial_reason: reason, outcome: "failure" });
    c.answer(session);
    await c.tick(1299);
    assert.equal(c.rendered.length, 0);
    assert.equal(c.els.diceCheckCard.classList.contains("crucial-failure"), false);
    await c.tick(1);
    assert.equal(c.els.diceOutcome.textContent, "DC 14　失敗");
    assert.equal(c.els.diceCheckCard.classList.contains("crucial-failure"), true);
    assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), false);
    assert.equal(c.els.diceCritical.hidden, true);
    await c.tick(1199);
    assert.equal(c.rendered.length, 0);
    await c.tick(1);
    await done;
    assert.equal(c.rendered[0], session);
    assert.equal(c.timers.size, 0);
    assert.doesNotMatch(c.els.diceBannerText.textContent, /大失敗/);
  }
});

test("short crucial results, disabled extremes and skipping retain selected-die semantics", async () => {
  for (const reducedMotion of [false, true]) {
    const c = client({ reducedMotion });
    const session = c.response(2, { in_combat: true });
    Object.assign(session.dice_log[0], { crucial: true, crucial_reason: "combat", outcome: "failure",
      critical_enabled: false, rolls: [20, 2], advantage: "disadvantage", selected_roll: 2, selected_index: 1 });
    const done = c.renderTurnResponse(session);
    await c.flush();
    if (!reducedMotion) {
      assert.equal(c.state.dicePresentation.minimum, 600);
      c.skipDicePresentation();
      await c.flush();
    }
    assert.equal(c.els.diceCheckCrucial.textContent, "失敗すると戦闘");
    assert.equal(c.els.diceFirst.classList.contains("discarded"), true);
    assert.equal(c.els.diceSecond.classList.contains("selected"), true);
    assert.equal(c.els.diceNatural.classList.contains("two-digits"), true);
    assert.equal(c.els.diceNaturalSecond.classList.contains("two-digits"), false);
    assert.equal(c.els.diceCheckCard.classList.contains("crucial-failure"), true);
    assert.equal(c.els.diceCheckCard.classList.contains("critical-success"), false);
    assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), false);
    assert.equal(c.els.diceCritical.hidden, true);
    await c.tick(1200);
    await done;
  }
});

test("only failed server-authorized crucial checks crack and stale effects are reset", async () => {
  for (const [crucial, outcome] of [[true, "success"], [false, "failure"]]) {
    const c = client({ reducedMotion: true });
    Object.assign(c.choice.check, { crucial: true, crucial_reason: "game_over" });
    c.els.diceCheckCard.classList.add("crucial-failure");
    c.openDiceCheck(c.choice, c.card);
    assert.equal(c.els.diceCheckCard.classList.contains("crucial-failure"), false);
    const done = c.confirmDiceCheck();
    const session = c.response(7);
    Object.assign(session.dice_log[0], { crucial, outcome, crucial_reason: "combat" });
    c.answer(session);
    await c.flush();
    assert.equal(c.els.diceCheckCard.classList.contains("crucial-failure"), false);
    assert.equal(c.els.diceCheckCrucial.hidden, !crucial);
    if (crucial) assert.equal(c.els.diceCheckCrucial.textContent, "失敗すると戦闘");
    await c.tick(1200);
    await done;
  }
});

test("crucial natural 1 keeps its exclusive critical label and combat-internal results bypass dice", async () => {
  const c = client({ reducedMotion: true });
  const session = c.response(1, { in_combat: true });
  Object.assign(session.dice_log[0], { crucial: true, crucial_reason: "combat", outcome: "critical_failure" });
  const done = c.renderTurnResponse(session);
  await c.flush();
  assert.equal(c.els.diceCritical.textContent, "大失敗");
  assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), true);
  await c.tick(1200);
  await done;
  const next = c.response(7, { in_combat: true });
  next.dice_log[0].crucial = true;
  await c.renderTurnResponse(next);
  assert.equal(c.els.diceCheckCard.style.display, "none");
  assert.equal(c.timers.size, 0);
});

test("both dice keep rolling without visible numbers until a slow server returns", async () => {
  const c = client();
  c.choice.check.advantage = "advantage";
  c.openDiceCheck(c.choice, c.card);
  const done = c.confirmDiceCheck();
  await c.tick(5000);
  assert.equal(c.els.diceSecond.hidden, false);
  assert.equal(c.els.diceNatural.hidden, true);
  assert.equal(c.els.diceNaturalSecond.hidden, true);
  assert.equal(c.els.diceCheckCard.classList.contains("rolling"), true);
  assert.equal(c.els.diceCheckCard.classList.contains("settling"), false);
  assert.equal(c.rendered.length, 0);
  const session = c.response(17);
  Object.assign(session.dice_log[0], { rolls: [3, 17], advantage: "advantage", selected_index: 1, selected_roll: 17 });
  c.answer(session);
  await c.tick(120);
  assert.equal(c.els.diceNatural.textContent, "3");
  assert.equal(c.els.diceNaturalSecond.textContent, "17");
  assert.equal(c.els.diceNaturalSecond.hidden, false);
  assert.equal(c.els.diceFirst.classList.contains("discarded"), true);
  assert.equal(c.els.diceSecond.classList.contains("selected"), true);
  await c.tick(1479);
  assert.equal(c.rendered.length, 0);
  await c.tick(1);
  await done;
  assert.equal(c.rendered.length, 1);
  assert.equal(c.timers.size, 0);
});

test("skipping during settling, number fade or calculation leaves no delayed animation", async () => {
  for (const elapsed of [600, 719, 720, 799, 800, 999]) {
    const c = client();
    const done = c.renderTurnResponse(c.response());
    await c.tick(elapsed);
    c.event("click");
    await c.flush();
    assert.equal(c.els.diceCheckCard.classList.contains("rolling"), false);
    assert.equal(c.els.diceCheckCard.classList.contains("settling"), false);
    assert.equal(c.els.diceCheckCard.classList.contains("instant-result"), true);
    assert.equal(c.els.diceNatural.hidden, false);
    assert.equal(c.els.diceOutcome.textContent, "DC 14　成功");
    c.event("click");
    await done;
    assert.equal(c.timers.size, 0);
    assert.equal(c.rendered.length, 1);
  }
});

test("a new roll clears the previous cracked pair, selection and visible numbers", async () => {
  const c = client();
  const first = c.renderTurnResponse(c.response(1));
  await c.tick(1000);
  assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), true);
  c.event("click");
  await first;
  c.openDiceCheck(c.choice, c.card);
  assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), false);
  assert.equal(c.els.diceCheckCard.classList.contains("faces-visible"), false);
  const next = c.confirmDiceCheck();
  assert.equal(c.els.diceNatural.hidden, true);
  assert.equal(c.els.diceNaturalSecond.hidden, true);
  assert.equal(c.els.diceSecond.hidden, true);
  c.answer(c.response(7));
  await c.tick(2500);
  await next;
  assert.equal(c.els.diceCheckCard.classList.contains("critical-failure"), false);
  assert.equal(c.timers.size, 0);
});
