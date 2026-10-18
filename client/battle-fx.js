/* Presentation consumes engine events; it never rolls or resolves combat. */
async function playCombatEvents(previous, next) {
  const combat = next.combat;
  if (!combat || previous?.combat?.id !== combat.id) return;
  const seen = Math.max(0, ...(previous.combat.log || []).map(entry => entry.sequence || 0));
  const events = (combat.events || []).filter(entry => entry.sequence > seen);
  if (!events.length) return;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const layer = document.querySelector("#combatFxLayer");
  const announcement = document.querySelector("#combatAnnouncement");
  const animations = new Set();
  const timers = new Set();
  const temporary = new Set();
  const logEntries = [...(previous.combat.log || [])];
  let finished = false;
  let resolvePlayback;
  const completion = new Promise(resolve => { resolvePlayback = resolve; });

  function later(callback, delay) {
    const timer = setTimeout(() => { timers.delete(timer); if (!finished) callback(); }, delay);
    timers.add(timer);
  }
  function animate(node, frames, duration, options = {}) {
    if (!node) return;
    const animation = node.animate(frames, { duration, easing: "ease-out", fill: "both", ...options });
    animations.add(animation);
    return animation;
  }
  function target(id) {
    if (id === "player") return document.querySelector(".player-combatant");
    return [...els.combatEnemies.children].find(node => node.dataset.combatTarget === id);
  }
  function position(node, className) {
    const rect = node.getBoundingClientRect();
    const root = layer.getBoundingClientRect();
    const effect = document.createElement("div");
    effect.className = className;
    effect.style.left = `${rect.left - root.left}px`;
    effect.style.top = `${rect.top - root.top}px`;
    effect.style.width = `${rect.width}px`;
    effect.style.height = `${rect.height}px`;
    layer.append(effect);
    temporary.add(effect);
    return effect;
  }
  function screenShake(duration, distance) {
    if (!reduced) animate(els.gameScreen, [0, -1, 1, -1, 1, 0].map(n => ({ transform: `translateX(${n * distance}px)` })), duration);
  }
  function resources(snapshot) {
    for (const [id, actor] of Object.entries(snapshot || {})) {
      const card = target(id);
      if (!card) continue;
      for (const stat of id === "player" ? ["hp", "mp", "sp"] : ["hp"]) {
        const row = card.querySelector(`.combat-resource.${stat}`);
        if (!row) continue;
        const bar = row.querySelector("b");
        const track = row.querySelector("i");
        const max = Math.max(1, Number(actor[`max_${stat}`] || 1));
        const value = Number(actor[stat] || 0);
        const width = `${Math.max(0, Math.min(100, value / max * 100))}%`;
        const before = bar.style.width;
        row.querySelector("strong").textContent = `${value}/${max}`;
        if (before === width) continue;
        const displayed = `${bar.getBoundingClientRect().width}px`;
        for (const animation of bar.getAnimations()) animation.cancel();
        bar.style.width = width;
        animate(bar, [{ width: displayed }, { width }], 400);
        if (stat === "hp" && !reduced && parseFloat(before) > parseFloat(width)) {
          const delay = document.createElement("em");
          delay.className = "combat-delay-bar";
          track.prepend(delay);
          temporary.add(delay);
          animate(delay, [{ width: displayed }, { width }], 400, { delay: 300 });
        }
      }
    }
  }
  function particles(card, kind) {
    if (reduced) return;
    const effect = position(card, `combat-impact impact-${kind}`);
    if (["physical", "holy", "rainbow"].includes(kind)) {
      animate(effect, [{ opacity: 0, transform: "scale(.65)" }, { opacity: 1, offset: .25 }, { opacity: 0, transform: "scale(1.15)" }], 300);
      return;
    }
    const healing = kind === "heal" || kind === "buff";
    for (let i = 0; i < 9; i++) {
      const bit = document.createElement("i");
      bit.style.left = `${20 + (i * 23) % 65}%`;
      bit.style.top = healing ? "82%" : `${28 + (i * 11) % 45}%`;
      effect.append(bit);
      animate(bit, [{ opacity: 0, transform: "translate(0,0) rotate(0deg)" }, { opacity: 1, offset: .2 },
        { opacity: 0, transform: `translate(${(i - 4) * 5}px,${healing ? -65 : (i % 2 ? -32 : 32)}px) rotate(${i * 35}deg)` }], healing ? 500 : 300);
    }
  }
  function number(card, visual, text) {
    if (!["damage", "heal", "miss"].includes(visual.kind)) return;
    const box = position(card, `combat-number ${visual.kind} ${visual.critical ? "critical" : ""}`);
    const label = document.createElement("span");
    label.textContent = visual.kind === "miss" ? "MISS" : `${visual.critical ? "CRITICAL " : ""}${visual.kind === "heal" ? "+" : ""}${visual.amount}`;
    box.append(label);
    animate(box, [{ opacity: 0, transform: "translateY(0)" }, { opacity: 1, offset: .12 },
      { opacity: 0, transform: reduced ? "translateY(0)" : "translateY(-30px)" }], 700);
    announcement.textContent = text;
  }
  function phase(entry) {
    const data = entry.data;
    const old = target(data.from_id);
    if (!old || !data.replacement) return;
    const ghost = position(old, "combat-phase-ghost");
    const oldImage = old.querySelector("img");
    if (oldImage) ghost.append(oldImage.cloneNode());
    const template = document.createElement("template");
    template.innerHTML = combatEnemyMarkup(data.replacement, entry.state?.[data.replacement.id]);
    const replacement = template.content.firstElementChild;
    old.replaceWith(replacement);
    animate(ghost, [{ opacity: 1 }, { opacity: 0 }], 500);
    animate(replacement, [{ opacity: 0 }, { opacity: 1 }], 500);
    if (!reduced) {
      const flash = document.createElement("div");
      flash.className = "combat-phase-flash";
      layer.append(flash);
      temporary.add(flash);
      animate(flash, [{ opacity: 0 }, { opacity: .9, offset: .2 }, { opacity: 0 }], 150);
      screenShake(400, 4);
    }
  }
  function event(entry) {
    logEntries.push(entry);
    els.combatLog.innerHTML = logEntries.slice(-40).map(combatLogMarkup).join("");
    els.combatLog.scrollTop = els.combatLog.scrollHeight;
    const visual = entry.visual;
    if (visual?.kind === "phase") phase(entry);
    resources(entry.state);
    if (!visual || visual.kind === "phase") return;
    const card = target(visual.target_id);
    if (!card) return;
    const portrait = card.querySelector("img") || card;
    number(card, visual, entry.text);
    if (visual.kind === "heal" || visual.kind === "buff") {
      particles(card, visual.kind);
      if (reduced) animate(card, [{ opacity: .65 }, { opacity: 1 }], 300);
    }
    if (["damage", "miss"].includes(visual.kind)) {
      if (!reduced && ["damage", "miss"].includes(entry.kind)) {
        const attacker = target(visual.actor_side === "party" ? "player" : visual.actor_id);
        const lunging = visual.actor_side === "party" ? attacker : attacker?.querySelector("img") || attacker;
        animate(lunging, [{ transform: "translateX(0)" }, { transform: `translateX(${visual.actor_side === "party" ? 12 : -12}px)` }, { transform: "translateX(0)" }], 160);
      }
      if (visual.kind === "miss") {
        if (!reduced) animate(portrait, [{ transform: "translateX(0)" }, { transform: "translateX(8px)" }, { transform: "translateX(0)" }], 240);
      } else if (!reduced) {
        if (visual.target_side === "enemy") {
          animate(portrait, [{ filter: "brightness(1)" }, { filter: "brightness(4)" }, { filter: "brightness(1)" }], 80);
          animate(portrait, [0, -6, 6, -6, 6, 0].map(x => ({ transform: `translateX(${x}px)` })), 240);
          const element = visual.weakness || visual.element === "rainbow" ? "rainbow" : ({ fire: "fire", ice: "ice", holy: "holy", light: "holy", physical: "physical", dark: "dark", cursed: "dark",
            earth: "earth", arcane: "arcane", water: "water" }[visual.element] || "physical");
          if (element) particles(card, element);
        } else {
          const background = getComputedStyle(card).backgroundColor;
          animate(card, [{ backgroundColor: background }, { backgroundColor: "var(--red-dim)" }, { backgroundColor: background }], 120);
          if (visual.heavy) screenShake(200, 4);
        }
      }
      if (visual.knocked_down && visual.target_side === "enemy") {
        animate(portrait, reduced ? [{ opacity: 1 }, { opacity: 0 }] :
          [{ filter: "grayscale(0)", transform: "translateY(0)", opacity: 1 },
            { filter: "grayscale(1)", transform: "translateY(16px)", opacity: 0 }], 600);
      }
    }
  }
  function skip(input) {
    if (input.type === "keydown" && input.code !== "Space") return;
    input.preventDefault();
    input.stopImmediatePropagation();
    finish(true);
  }
  function finish(skipped = false) {
    if (finished) return;
    finished = true;
    for (const timer of timers) clearTimeout(timer);
    for (const animation of animations) animation.cancel();
    for (const node of temporary) node.remove();
    document.removeEventListener("click", skip, true);
    document.removeEventListener("keydown", skip, true);
    if (skipped) announcement.textContent = events.filter(entry => entry.visual).map(entry => entry.text).join(" ");
    state.combatPlayback = null;
    resolvePlayback();
  }
  state.combatPlayback = { skip: () => finish(true) };
  document.addEventListener("click", skip, true);
  document.addEventListener("keydown", skip, true);
  const terminal = combat.status !== "active";
  const actionEvents = events.filter(entry => !["victory", "defeat", "fled", "purified"].includes(entry.kind));
  // Overlap effects and compress long multi-hit sequences into the same 1.4s budget.
  const interval = Math.min(240, 400 / Math.max(1, actionEvents.length - 1));
  actionEvents.forEach((entry, index) => index ? later(() => event(entry), index * interval) : event(entry));
  const end = Math.max(0, actionEvents.length - 1) * interval + 700;
  later(() => resources(combat.presentation_state), Math.max(0, end - 700));
  later(finish, end + (terminal ? 300 : 0));
  await completion;
}
