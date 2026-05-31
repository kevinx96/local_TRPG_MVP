/* ═══════════════════════════════════════════════════
   Local TRPG — Client Application
   ═══════════════════════════════════════════════════ */

const state = {
  sessionId: null,
};

/* ── DOM References ── */
const els = {
  /* Start screen */
  startScreen:     document.querySelector("#startScreen"),
  gameScreen:      document.querySelector("#gameScreen"),
  heroNameInput:   document.querySelector("#heroNameInput"),
  startButton:     document.querySelector("#startButton"),
  startBtnText:    document.querySelector(".start-btn-text"),
  startBtnLoading: document.querySelector(".start-btn-loading"),
  backendStatus:   document.querySelector("#backendStatus"),

  /* Game screen */
  newSessionButton:    document.querySelector("#newSessionButton"),
  sceneTitle:          document.querySelector("#sceneTitle"),
  backendInfo:         document.querySelector("#backendInfo"),
  messages:            document.querySelector("#messages"),
  form:                document.querySelector("#turnForm"),
  input:               document.querySelector("#playerInput"),
  sendButton:          document.querySelector("#sendButton"),
  characterName:       document.querySelector("#characterName"),
  characterDescription:document.querySelector("#characterDescription"),
  inventory:           document.querySelector("#inventory"),
  diceLog:             document.querySelector("#diceLog"),
  systemLogs:          document.querySelector("#systemLogs"),
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

/* ═══════════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════════ */

async function init() {
  await loadConfig();
}

async function loadConfig() {
  try {
    const config = await fetchJson("/api/config");
    const info = `${config.active_backend} / ${config.model}`;
    els.backendInfo.textContent = info;
    els.backendStatus.textContent = `✓ ${info}`;
  } catch {
    els.backendInfo.textContent = "設定を取得できません";
    els.backendStatus.textContent = "⚠ バックエンドに接続できません";
  }
}

/* ═══════════════════════════════════════════════════
   START SCREEN → SESSION CREATION
   ═══════════════════════════════════════════════════ */

async function startGame() {
  const heroName = els.heroNameInput.value.trim() || "アルス";
  setStartBusy(true);
  try {
    const session = await fetchJson("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_path: "host/prompt/text/dragon_rpg.txt",
        character: { name: heroName },
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
  els.sceneTitle.textContent = session.current_scene || session.scenario_title || "開始";

  /* Character info */
  els.characterName.textContent = character.name || "冒険者";
  els.characterDescription.textContent = character.description || "";

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
  renderChoices(session.choices || []);
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
}

function hideChoices() {
  els.choicesArea.style.display = "none";
  els.choicesList.innerHTML = "";
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
  els.messages.append(node);
  els.messages.scrollTop = els.messages.scrollHeight;
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

/* Allow Enter (without Shift) in name input to start */
els.heroNameInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    startGame();
  }
});

/* Boot */
init();
