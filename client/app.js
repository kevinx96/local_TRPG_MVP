/* ═══════════════════════════════════════════════════
   Local TRPG — Client Application
   ═══════════════════════════════════════════════════ */

const state = {
  sessionId: null,
  pendingChoices: [],
  choicesRevealed: false,
  selectedCharacterId: "hero",
  selectedCharacterImage: "/static/images/char_male_hero.png",
  selectedCharacter: null,
  characters: [],
  expandedCharacterId: "",
  scenarioPath: "host/prompt/processed/dragon_rpg.json",
};

/* ── DOM References ── */
const els = {
  /* Start screen */
  startScreen:     document.querySelector("#startScreen"),
  gameScreen:      document.querySelector("#gameScreen"),
  backendSelect:   document.querySelector("#backendSelect"),
  modelSelect:     document.querySelector("#modelSelect"),
  gmModeInputs:    document.querySelectorAll('input[name="gmMode"]'),
  scenarioSelect:  document.querySelector("#scenarioSelect"),
  characterCards:  document.querySelector("#characterCards"),
  heroNameInput:   document.querySelector("#heroNameInput"),
  genderSelect:    document.querySelector("#genderSelect"),
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
  enemyPanel:      document.querySelector("#enemyPanel"),
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
  restoreGmMode();
  await loadConfig();
  await loadScenarios();
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

async function loadScenarios() {
  try {
    const data = await fetchJson("/api/scenarios");
    const scenarios = data.scenarios || [];
    els.scenarioSelect.innerHTML = scenarios
      .map((s) => `<option value="${escapeHtml(s.filename)}">${escapeHtml(s.title || s.filename)}</option>`)
      .join("");
    const preferred = scenarios.find((s) => s.filename === "dragon_rpg.json") || scenarios[0];
    if (preferred) {
      els.scenarioSelect.value = preferred.filename;
      await onScenarioChange();
    }
    els.scenarioSelect.addEventListener("change", onScenarioChange);
  } catch (err) {
    els.backendStatus.textContent = `剧本加载失败: ${err.message}`;
  }
}

async function onScenarioChange() {
  const filename = els.scenarioSelect.value;
  if (!filename) return;
  try {
    const data = await fetchJson(`/api/scenarios/${encodeURIComponent(filename)}`);
    const characters = data.scenario?.characters || [];
    state.scenarioPath = `host/prompt/processed/${filename}`;
    state.expandedCharacterId = "";
    renderCharacterCards(characters);
  } catch (err) {
    els.characterCards.innerHTML = `<p class="start-backend">角色加载失败</p>`;
  }
}

function renderCharacterCards(characters) {
  state.characters = Array.isArray(characters) ? characters : [];
  if (!characters.length) {
    state.selectedCharacterId = "";
    state.selectedCharacterImage = "";
    state.selectedCharacter = null;
    state.characters = [];
    state.expandedCharacterId = "";
    els.heroNameInput.value = "";
    els.genderSelect.style.display = "none";
    els.characterCards.innerHTML = `<p class="start-backend">本剧本暂无角色定义</p>`;
    return;
  }
  const selectedId = characters.some((char) => char.id === state.selectedCharacterId)
    ? state.selectedCharacterId
    : characters[0].id;
  const expandedId = characters.some((char) => char.id === state.expandedCharacterId)
    ? state.expandedCharacterId
    : "";
  els.characterCards.innerHTML = characters.map((char) => {
    const attrs = char.attributes || {};
    const attrText = Object.entries(attrs)
      .map(([k, v]) => `<span class="char-attr">${escapeHtml(k)} ${v}</span>`)
      .join("");
    const inventoryText = (char.inventory || [])
      .map((item) => `${item.name || ""}${item.quantity ? ` x${item.quantity}` : ""}`)
      .filter(Boolean)
      .map((text) => `<span class="char-chip">${escapeHtml(text)}</span>`)
      .join("");
    const equipmentText = (char.equipment || [])
      .map((text) => `<span class="char-chip">${escapeHtml(text)}</span>`)
      .join("");
    const isSelected = char.id === selectedId;
    const isExpanded = char.id === expandedId;
    const img = char.image || "";
    return `<button class="char-card ${isSelected ? "selected" : ""} ${isExpanded ? "expanded" : ""}" data-char-id="${escapeAttr(char.id)}" type="button" aria-expanded="${isExpanded ? "true" : "false"}">
      <div class="char-card-summary">
        <strong>${escapeHtml(char.name || char.id)}</strong>
        <span class="char-card-chevron">⌄</span>
      </div>
      <div class="char-card-details" ${isExpanded ? "" : "hidden"}>
        <div class="char-card-img" style="background-image:url('${escapeAttr(img)}')"></div>
        <div class="char-card-info">
          <span class="char-card-stats">HP ${char.hp}/${char.max_hp} MP ${char.mp}/${char.max_mp} SP ${char.sp}/${char.max_sp}</span>
          ${char.description ? `<p class="char-card-desc">${escapeHtml(char.description)}</p>` : ""}
          <div class="char-card-attrs">${attrText}</div>
          ${equipmentText ? `<div class="char-card-line"><span>装備</span><div>${equipmentText}</div></div>` : ""}
          ${inventoryText ? `<div class="char-card-line"><span>所持</span><div>${inventoryText}</div></div>` : ""}
        </div>
      </div>
    </button>`;
  }).join("");

  document.querySelectorAll(".char-card").forEach((card) => {
    card.addEventListener("click", () => {
      const charId = card.dataset.charId;
      const char = characters.find((c) => c.id === charId);
      if (char) selectCharacter(char, { expanded: state.expandedCharacterId !== charId });
    });
  });
  const selected = characters.find((char) => char.id === selectedId) || characters[0];
  selectCharacter(selected, { render: false });
}

function selectCharacter(char, options = {}) {
  state.selectedCharacterId = char.id;
  state.selectedCharacter = char;
  els.heroNameInput.value = char.default_name || char.name || "";
  if (char.id === "hero") {
    els.genderSelect.style.display = "flex";
    updateHeroImage(char);
  } else {
    els.genderSelect.style.display = "none";
    state.selectedCharacterImage = char.image || "";
  }
  if (Object.prototype.hasOwnProperty.call(options, "expanded")) {
    state.expandedCharacterId = options.expanded ? char.id : "";
  }
  if (options.render === false) return;
  document.querySelectorAll(".char-card").forEach((card) => {
    const selected = card.dataset.charId === char.id;
    const expanded = card.dataset.charId === state.expandedCharacterId;
    card.classList.toggle("selected", selected);
    card.classList.toggle("expanded", expanded);
    card.setAttribute("aria-expanded", expanded ? "true" : "false");
    const details = card.querySelector(".char-card-details");
    if (details) details.hidden = !expanded;
  });
}

function updateHeroImage(char) {
  const gender = document.querySelector('input[name="heroGender"]:checked')?.value || "男勇者";
  state.selectedCharacterImage = gender === "女勇者" && char.image_female
    ? char.image_female
    : char.image || "";
}

async function startGame() {
  const heroName = els.heroNameInput.value.trim() || "アルス";
  const backend = els.backendSelect ? els.backendSelect.value : "ollama";
  const model = els.modelSelect ? els.modelSelect.value : "";
  const gmMode = document.querySelector('input[name="gmMode"]:checked')?.value || "semi";
  const scenarioPath = state.scenarioPath;
  const selectedCharacter = currentSelectedCharacter();
  const characterId = selectedCharacter?.id || state.selectedCharacterId;
  const characterImage = characterImageForStart(selectedCharacter);
  localStorage.setItem("trpg.gmMode", gmMode);
  setStartBusy(true);
  try {
    // Update config first
    await fetch("/api/config", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ active_backend: backend, model })
    });
    await loadConfig();

    const charPayload = {
      name: heroName,
      character_image: characterImage,
    };
    const session = await fetchJson("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        scenario_path: scenarioPath,
        gm_mode: gmMode,
        character_id: characterId,
        character: charPayload,
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

function currentSelectedCharacter() {
  const selectedCardId = document.querySelector(".char-card.selected")?.dataset.charId || state.selectedCharacterId;
  const selected = state.characters.find((char) => char.id === selectedCardId)
    || state.characters.find((char) => char.id === state.selectedCharacterId)
    || state.selectedCharacter;
  if (selected) {
    state.selectedCharacterId = selected.id;
    state.selectedCharacter = selected;
  }
  return selected || null;
}

function characterImageForStart(char) {
  if (!char) return state.selectedCharacterImage || "";
  if (char.id === "hero") {
    updateHeroImage(char);
    return state.selectedCharacterImage || char.image || "";
  }
  state.selectedCharacterImage = char.image || "";
  return state.selectedCharacterImage;
}

function restoreGmMode() {
  const saved = localStorage.getItem("trpg.gmMode") || "semi";
  for (const input of els.gmModeInputs || []) {
    input.checked = input.value === saved;
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
  if (els.sceneTitle) els.sceneTitle.textContent = session.current_scene_title || session.current_scene || session.scenario_title || "開始";

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
  renderEnemies(session.enemies || []);

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

function renderEnemies(enemies) {
  if (!els.enemyPanel) return;
  if (!Array.isArray(enemies) || !enemies.length) {
    els.enemyPanel.style.display = "none";
    els.enemyPanel.innerHTML = "";
    return;
  }

  els.enemyPanel.innerHTML = enemies.map((enemy) => {
    const name = enemy.name || enemy.title || enemy.id || "敵";
    const hp = Number(enemy.hp ?? 0);
    const maxHp = Number(enemy.max_hp || hp || 1);
    const percent = Math.max(0, Math.min(100, (hp / maxHp) * 100));
    const skills = Array.isArray(enemy.skills)
      ? enemy.skills.slice(0, 3).map((skill) => `<span>${escapeHtml(skillLabel(skill))}</span>`).join("")
      : "";
    return `<section class="enemy-card">
      <div class="enemy-card-head">
        <strong>${escapeHtml(name)}</strong>
        <span>HP ${hp}/${maxHp}</span>
      </div>
      <div class="enemy-hp"><i style="width:${percent}%"></i></div>
      ${enemy.description ? `<p>${escapeHtml(enemy.description)}</p>` : ""}
      ${skills ? `<div class="enemy-skills">${skills}</div>` : ""}
    </section>`;
  }).join("");
  els.enemyPanel.style.display = "";
}

function skillLabel(skill) {
  if (typeof skill === "string") return skill;
  if (skill && typeof skill === "object") return skill.name || skill.id || skill.description || "技能";
  return "技能";
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
    card.className = `choice-card ${isCombatChoice(text, preview, risk) ? "combat-choice" : ""}`;

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

function isCombatChoice(text, preview, risk) {
  const source = `${text} ${preview} ${risk}`;
  return /攻撃|防御|回避|撤退|戦闘|敵|斬|剣|魔法|回復|ダメージ|1d20|DC\d+/i.test(source);
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

function escapeAttr(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
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
for (const input of els.gmModeInputs || []) {
  input.addEventListener("change", () => {
    if (input.checked) localStorage.setItem("trpg.gmMode", input.value);
  });
}
for (const input of document.querySelectorAll('input[name="heroGender"]')) {
  input.addEventListener("change", () => {
    if (state.selectedCharacterId === "hero" && state.selectedCharacter) {
      const char = state.selectedCharacter;
      const image = input.value === "女勇者" && char.image_female
        ? char.image_female
        : char.image || "";
      state.selectedCharacterImage = image;
    }
  });
}

// Config gear panel toggle
const configPanel = document.querySelector("#configPanel");
const configToggle = document.querySelector("#configToggle");
if (configToggle && configPanel) {
  configToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    configPanel.classList.toggle("open");
  });
  document.addEventListener("click", (e) => {
    if (!configPanel.contains(e.target)) {
      configPanel.classList.remove("open");
    }
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
