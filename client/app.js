/* ═══════════════════════════════════════════════════
   Local TRPG — Client Application
   ═══════════════════════════════════════════════════ */

const state = {
  sessionId: null,
  pendingChoices: [],
  choicesRevealed: false,
};

/* ── DOM References ── */
const els = {
  /* Start screen */
  startScreen:     document.querySelector("#startScreen"),
  gameScreen:      document.querySelector("#gameScreen"),
  backendSelect:   document.querySelector("#backendSelect"),
  modelSelect:     document.querySelector("#modelSelect"),
  heroNameInput:   document.querySelector("#heroNameInput"),
  startButton:     document.querySelector("#startButton"),
  startBtnText:    document.querySelector(".start-btn-text"),
  startBtnLoading: document.querySelector(".start-btn-loading"),
  backendStatus:   document.querySelector("#backendStatus"),

  /* Game screen */
  background:      document.querySelector("#background"),
  portrait:        document.querySelector("#portrait"),
  menuToggleBtn:   document.querySelector("#menuToggleBtn"),
  dialogueBox:     document.querySelector("#dialogueBox"),
  speakerName:     document.querySelector("#speakerName"),
  messageText:     document.querySelector("#messageText"),
  logToggleBtn:    document.querySelector("#logToggleBtn"),
  inputToggleBtn:  document.querySelector("#inputToggleBtn"),
  logOverlay:      document.querySelector("#logOverlay"),
  menuOverlay:     document.querySelector("#menuOverlay"),
  logCloseBtn:     document.querySelector("#logCloseBtn"),
  menuCloseBtn:    document.querySelector("#menuCloseBtn"),
  newSessionButton:document.querySelector("#newSessionButton"),
  sceneTitle:      document.querySelector("#sceneTitle"),
  backendInfo:     document.querySelector("#backendInfo"),
  messages:        document.querySelector("#messages"),
  form:            document.querySelector("#turnForm"),
  input:           document.querySelector("#playerInput"),
  sendButton:      document.querySelector("#sendButton"),
  clickIndicator:  document.querySelector("#clickIndicator"),
  characterName:   document.querySelector("#characterName"),
  characterDescription:document.querySelector("#characterDescription"),
  inventory:       document.querySelector("#inventory"),
  diceLog:         document.querySelector("#diceLog"),
  systemLogs:      document.querySelector("#systemLogs"),
  hpBar:  document.querySelector("#hpBar"),
  mpBar:  document.querySelector("#mpBar"),
  spBar:  document.querySelector("#spBar"),
  hpText: document.querySelector("#hpText"),
  mpText: document.querySelector("#mpText"),
  spText: document.querySelector("#spText"),
  goldText: document.querySelector("#goldText"),
  choicesArea: document.querySelector("#choicesArea"),
  choicesList: document.querySelector("#choicesList"),
};

let cachedConfig = null;

/* ═══════════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════════ */

async function init() {
  await loadConfig();
}

async function loadConfig() {
  try {
    const config = await fetchJson("/api/config");
    cachedConfig = config;

    if (els.backendSelect && config.backends) {
      els.backendSelect.innerHTML = "";
      for (const key of Object.keys(config.backends)) {
        const opt = document.createElement("option");
        opt.value = key;
        opt.textContent = key.toUpperCase();
        if (key === config.active_backend) opt.selected = true;
        els.backendSelect.appendChild(opt);
      }
    }
    populateModelSelect(config);

    const info = `${config.active_backend} / ${config.model}`;
    if (els.backendInfo) els.backendInfo.textContent = info;
    if (els.backendStatus) els.backendStatus.textContent = `✓ ${info}`;
  } catch {
    if (els.backendInfo) els.backendInfo.textContent = "設定を取得できません";
    if (els.backendStatus) els.backendStatus.textContent = "⚠ バックエンドに接続できません";
  }
}

function populateModelSelect(config) {
  if (!els.modelSelect || !config.backends) return;
  const backendName = els.backendSelect?.value || config.active_backend;
  const backend = config.backends[backendName] || {};
  const models = uniqueList([backend.model, ...(backend.fallback_models || [])]);

  els.modelSelect.innerHTML = "";
  for (const model of models) {
    const opt = document.createElement("option");
    opt.value = model;
    opt.textContent = model;
    if (backendName === config.active_backend && model === config.model) opt.selected = true;
    els.modelSelect.appendChild(opt);
  }
}

function uniqueList(values) {
  return values.filter((value, index, array) => value && array.indexOf(value) === index);
}

/* ═══════════════════════════════════════════════════
   START SCREEN → SESSION CREATION
   ═══════════════════════════════════════════════════ */

async function startGame() {
  const heroName = els.heroNameInput.value.trim() || "アルス";
  const heroGender = document.querySelector('input[name="heroGender"]:checked')?.value || "男勇者";
  const backend = els.backendSelect ? els.backendSelect.value : "ollama";
  const model = els.modelSelect ? els.modelSelect.value : "";
  setStartBusy(true);
  try {
    // Update config first
    await fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_backend: backend, model })
    });
    await loadConfig();

    const session = await fetchJson("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_path: "host/prompt/text/dragon_rpg.txt",
        character: { 
          name: heroName,
          description: heroGender,
          character_image: heroGender === "女勇者" ? "/static/images/char_female_hero.png" : "/static/images/char_male_hero.png"
        },
      }),
    });
    state.sessionId = session.id;
    /* Transition to game screen */
    els.startScreen.style.display = "none";
    els.gameScreen.style.display = "";
    renderSession(session);
  } catch (err) {
    els.backendStatus.textContent = `エラー: ${err.message}`;
  } finally {
    setStartBusy(false);
  }
}

function setStartBusy(busy) {
  els.startButton.disabled = busy;
  els.heroNameInput.disabled = busy;
  els.startBtnText.style.display = busy ? "none" : "";
  els.startBtnLoading.style.display = busy ? "" : "none";
}

/* New session from game screen */
async function newSession() {
  /* Show start screen again */
  state.pendingChoices = [];
  state.choicesRevealed = false;
  els.gameScreen.style.display = "none";
  els.startScreen.style.display = "";
  els.messages.innerHTML = "";
  hideChoices();
}

/* ═══════════════════════════════════════════════════
   TURN SUBMISSION
   ═══════════════════════════════════════════════════ */

async function submitTurn(event) {
  event.preventDefault();
  const text = els.input.value.trim();
  if (!text || !state.sessionId) return;
  els.input.value = "";
  addMessage("user", "プレイヤー", text);
  hideChoices();
  clearPendingChoices();
  setBusy(true);
  try {
    const response = await fetch(`/api/sessions/${state.sessionId}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!response.ok || !response.body) {
      throw new Error(await response.text());
    }
    renderSession(await response.json());
  } catch (error) {
    addMessage("assistant", "GM", `エラー: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

/* Submit a choice as a turn */
async function submitChoice(choiceText) {
  if (!choiceText || !state.sessionId) return;
  addMessage("user", "プレイヤー", choiceText);
  hideChoices();
  clearPendingChoices();
  setBusy(true);
  try {
    const response = await fetch(`/api/sessions/${state.sessionId}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: choiceText }),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    renderSession(await response.json());
  } catch (error) {
    addMessage("assistant", "GM", `エラー: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

/* ═══════════════════════════════════════════════════
   RENDER SESSION STATE
   ═══════════════════════════════════════════════════ */

function renderSession(session) {
  state.sessionId = session.id;
  const character = session.character;

  /* Scene */
  if (els.sceneTitle) els.sceneTitle.textContent = session.current_scene || session.scenario_title || "開始";

  if (els.background) {
    if (character.background_image) {
      els.background.style.backgroundImage = `url(${character.background_image})`;
    } else {
      els.background.style.backgroundImage = "";
    }
  }

  if (els.portrait) {
    if (character.character_image) {
      els.portrait.src = character.character_image;
      els.portrait.style.display = "";
    } else {
      els.portrait.style.display = "none";
    }
  }

  /* Character info */
  if (els.characterName) els.characterName.textContent = character.name || "冒険者";
  if (els.characterDescription) els.characterDescription.textContent = character.description || "";

  /* Meters */
  renderMeter("hp", character);
  renderMeter("mp", character);
  renderMeter("sp", character);
  els.goldText.textContent = Number(character.gold || 0).toLocaleString("ja-JP");

  /* Inventory (item objects) */
  renderInventory(character.inventory || []);

  /* Dice log */
  renderList(
    els.diceLog,
    (session.dice_log || []).slice(-5).reverse().map(
      (roll) => `🎲 ${roll.expression}: ${roll.rolls.join(", ")} = ${roll.total}`
    ),
    "判定なし",
  );

  /* System logs */
  renderList(
    els.systemLogs,
    (session.system_logs || []).slice(-8).reverse().map((entry) => entry.text),
    "ログなし",
  );

  /* Messages */
  renderMessages(session.messages || []);

  /* Choices */
  setPendingChoices(session.choices || []);
}

/* ═══════════════════════════════════════════════════
   METERS
   ═══════════════════════════════════════════════════ */

function renderMeter(stat, character) {
  const value = Number(character[stat] || 0);
  const max = Number(character[`max_${stat}`] || value || 1);
  const percent = Math.max(0, Math.min(100, (value / max) * 100));
  els[`${stat}Bar`].style.width = `${percent}%`;
  els[`${stat}Text`].textContent = `${value}/${max}`;
}

/* ═══════════════════════════════════════════════════
   INVENTORY (with descriptions)
   ═══════════════════════════════════════════════════ */

function renderInventory(items) {
  els.inventory.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "inventory-item";
    li.innerHTML = `<div class="item-header"><span class="item-name" style="color:var(--muted)">所持品なし</span></div>`;
    els.inventory.append(li);
    return;
  }
  for (const item of items) {
    const name = typeof item === "string" ? item : (item.name || "不明");
    const desc = typeof item === "object" ? (item.description || "") : "";
    const effect = typeof item === "object" ? (item.effect || "") : "";
    const qty = typeof item === "object" ? (item.quantity || 1) : 1;

    const li = document.createElement("li");
    li.className = "inventory-item";

    const hasDetails = desc || effect;

    li.innerHTML = `
      <div class="item-header">
        <span class="item-name">${escapeHtml(name)}</span>
        <span style="display:flex;align-items:center;gap:6px">
          <span class="item-qty">×${qty}</span>
          ${hasDetails ? '<span class="item-toggle">▼</span>' : ''}
        </span>
      </div>
      ${hasDetails ? `
        <div class="item-details">
          ${desc ? `<div class="item-desc">${escapeHtml(desc)}</div>` : ''}
          ${effect ? `<div class="item-effect">${escapeHtml(effect)}</div>` : ''}
        </div>
      ` : ''}
    `;

    if (hasDetails) {
      li.addEventListener("click", () => li.classList.toggle("expanded"));
    }

    els.inventory.append(li);
  }
}

/* ═══════════════════════════════════════════════════
   CHOICES
   ═══════════════════════════════════════════════════ */

function renderChoices(choices) {
  if (!choices || !choices.length) {
    hideChoices();
    return;
  }

  els.choicesList.innerHTML = "";
  for (let i = 0; i < choices.length; i++) {
    const choice = choices[i];
    const text = typeof choice === "string" ? choice : (choice.text || "");
    const preview = typeof choice === "object" ? (choice.preview || "") : "";
    const risk = typeof choice === "object" ? (choice.risk || "") : "";

    const card = document.createElement("button");
    card.type = "button";
    card.className = "choice-card";

    const riskClass = classifyRisk(risk);

    card.innerHTML = `
      <div class="choice-number">${i + 1}</div>
      <div class="choice-body">
        <div class="choice-text">${escapeHtml(text)}</div>
        ${preview ? `<div class="choice-preview">${escapeHtml(preview)}</div>` : ''}
        ${risk ? `<span class="choice-risk ${riskClass}">${escapeHtml(risk)}</span>` : ''}
      </div>
    `;

    card.addEventListener("click", () => submitChoice(text));
    els.choicesList.append(card);
  }

  els.choicesArea.style.display = "";
  els.dialogueBox.classList.remove("choices-ready");
  if (els.clickIndicator) els.clickIndicator.style.display = "none";
}

function hideChoices() {
  els.choicesArea.style.display = "none";
  els.choicesList.innerHTML = "";
}

function setPendingChoices(choices) {
  state.pendingChoices = Array.isArray(choices) ? choices : [];
  state.choicesRevealed = false;
  hideChoices();
  updateDialogueAdvanceState();
}

function clearPendingChoices() {
  state.pendingChoices = [];
  state.choicesRevealed = false;
  updateDialogueAdvanceState();
}

function revealPendingChoices() {
  if (state.choicesRevealed || !state.pendingChoices.length) return;
  state.choicesRevealed = true;
  renderChoices(state.pendingChoices);
}

function updateDialogueAdvanceState() {
  const hasChoices = state.pendingChoices.length > 0 && !state.choicesRevealed;
  els.dialogueBox.classList.toggle("choices-ready", hasChoices);
  if (els.clickIndicator) {
    els.clickIndicator.style.display = hasChoices ? "" : "none";
  }
}

function classifyRisk(risk) {
  if (!risk) return "safe";
  const lower = risk.toLowerCase();
  if (lower.includes("判定不要") || lower.includes("安全") || lower.includes("リスクなし")) {
    return "safe";
  }
  if (lower.includes("危険") || lower.includes("リスク") || lower.includes("ダメージ")) {
    return "danger";
  }
  return "check"; /* dice check needed */
}

/* ═══════════════════════════════════════════════════
   MESSAGES
   ═══════════════════════════════════════════════════ */

function renderMessages(messages) {
  els.messages.innerHTML = "";
  for (const message of messages) {
    addMessage(message.role, message.speaker, message.text);
  }
}

function addMessage(role, speaker, text) {
  const node = document.createElement("article");
  node.className = `message ${role === "user" ? "user" : "assistant"}`;

  const speakerNode = document.createElement("span");
  speakerNode.className = "speaker";
  speakerNode.textContent = speaker || (role === "user" ? "プレイヤー" : "GM");

  const textNode = document.createElement("div");
  textNode.className = "text";
  textNode.textContent = text || "";

  node.append(speakerNode, textNode);
  if (els.messages) {
    els.messages.append(node);
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  // Update galgame dialog box
  if (els.speakerName) els.speakerName.textContent = speaker || (role === "user" ? "プレイヤー" : "GM");
  if (els.messageText) els.messageText.textContent = text || "";

  return textNode;
}

/* ═══════════════════════════════════════════════════
   GENERIC LIST RENDERER
   ═══════════════════════════════════════════════════ */

function renderList(target, items, emptyText) {
  target.innerHTML = "";
  const values = items.length ? items : [emptyText];
  for (const item of values) {
    const li = document.createElement("li");
    li.textContent = item;
    target.append(li);
  }
}

/* ═══════════════════════════════════════════════════
   UTILITIES
   ═══════════════════════════════════════════════════ */

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function setBusy(isBusy) {
  els.sendButton.disabled = isBusy;
  els.newSessionButton.disabled = isBusy;
  if (isBusy) {
    els.input.placeholder = "GMが応答中…";
  } else {
    els.input.placeholder = "自分で行動を入力…";
  }
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

/* ═══════════════════════════════════════════════════
   EVENT BINDINGS
   ═══════════════════════════════════════════════════ */

els.form.addEventListener("submit", submitTurn);
els.startButton.addEventListener("click", startGame);
els.newSessionButton.addEventListener("click", newSession);
if (els.backendSelect) {
  els.backendSelect.addEventListener("change", () => {
    if (cachedConfig) populateModelSelect(cachedConfig);
  });
}

// Galgame Overlay Toggles
if (els.menuToggleBtn) els.menuToggleBtn.addEventListener("click", () => els.menuOverlay.style.display = "");
if (els.menuCloseBtn) els.menuCloseBtn.addEventListener("click", () => els.menuOverlay.style.display = "none");
if (els.logToggleBtn) els.logToggleBtn.addEventListener("click", () => els.logOverlay.style.display = "");
if (els.logCloseBtn) els.logCloseBtn.addEventListener("click", () => els.logOverlay.style.display = "none");
if (els.inputToggleBtn) els.inputToggleBtn.addEventListener("click", () => {
  els.form.style.display = els.form.style.display === "none" ? "" : "none";
});
if (els.dialogueBox) {
  els.dialogueBox.addEventListener("click", revealPendingChoices);
  els.dialogueBox.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      revealPendingChoices();
    }
  });
}

/* Allow Enter (without Shift) in name input to start */
els.heroNameInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    startGame();
  }
});

/* Boot */
init();
