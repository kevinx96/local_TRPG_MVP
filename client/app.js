/* ═══════════════════════════════════════════════════
   Local TRPG — Client Application
   ═══════════════════════════════════════════════════ */

const state = {
  sessionId: null,
  pendingChoices: [],
  choiceStack: [],
  choicesRevealed: false,
  selectedCharacterId: "hero",
  selectedCharacterImage: "/static/images/char_male_hero_v2.png",
  selectedCharacter: null,
  characters: [],
  expandedCharacterId: "",
  scenarioPath: "host/prompt/processed/dragon_rpg.json",
  lastDiceLogLength: 0,
  lastDiceSignature: "",
  diceAnimationTimer: null,
  nextDiceDc: 0,
  nextDiceType: "1d20",
  character: null,
  combatTargetId: "",
  combatActionTab: "attack",
  combatBusy: false,
  combatActions: [],
  combatIntroSeenId: "",
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
  genderSection:   document.querySelector("#genderSection"),
  genderSelect:    document.querySelector("#genderSelect"),
  startButton:     document.querySelector("#startButton"),
  startBtnText:    document.querySelector(".start-btn-text"),
  startBtnLoading: document.querySelector(".start-btn-loading"),
  backendStatus:   document.querySelector("#backendStatus"),

  /* Game screen */
  background:      document.querySelector("#background"),
  spriteLayer:     document.querySelector("#spriteLayer"),
  locationPortraits:document.querySelector("#locationPortraits"),
  playerPortrait:  document.querySelector("#playerPortrait"),
  npcPortrait:     document.querySelector("#npcPortrait"),
  menuToggleBtn:   document.querySelector("#menuToggleBtn"),
  dialogueBox:     document.querySelector("#dialogueBox"),
  speakerName:     document.querySelector("#speakerName"),
  messageText:     document.querySelector("#messageText"),
  diceBanner:      document.querySelector("#diceBanner"),
  diceBannerText:  document.querySelector("#diceBannerText"),
  diceRollFace:    document.querySelector(".dice-roll-face"),
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
  characterAttributes:document.querySelector("#characterAttributes"),
  companionInfo:   document.querySelector("#companionInfo"),
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
  combatScreen: document.querySelector("#combatScreen"),
  combatIntro: document.querySelector("#combatIntro"),
  combatIntroText: document.querySelector("#combatIntroText"),
  combatIntroContinue: document.querySelector("#combatIntroContinue"),
  combatTitle: document.querySelector("#combatTitle"),
  combatRound: document.querySelector("#combatRound"),
  combatPlayerName: document.querySelector("#combatPlayerName"),
  combatPlayerImage: document.querySelector("#combatPlayerImage"),
  combatPlayerHp: document.querySelector("#combatPlayerHp"),
  combatPlayerMp: document.querySelector("#combatPlayerMp"),
  combatPlayerSp: document.querySelector("#combatPlayerSp"),
  combatPlayerHpBar: document.querySelector("#combatPlayerHpBar"),
  combatPlayerMpBar: document.querySelector("#combatPlayerMpBar"),
  combatPlayerSpBar: document.querySelector("#combatPlayerSpBar"),
  combatEnemies: document.querySelector("#combatEnemies"),
  combatLog: document.querySelector("#combatLog"),
  combatActionTabs: document.querySelector("#combatActionTabs"),
  combatActions: document.querySelector("#combatActions"),
  combatResult: document.querySelector("#combatResult"),
  combatResultTitle: document.querySelector("#combatResultTitle"),
  combatResultText: document.querySelector("#combatResultText"),
  combatResolveButton: document.querySelector("#combatResolveButton"),
  endingOverlay: document.querySelector("#endingOverlay"),
  endingTitle: document.querySelector("#endingTitle"),
  endingReason: document.querySelector("#endingReason"),
  endingRestartButton: document.querySelector("#endingRestartButton"),
};

let cachedConfig = null;

function choiceDebug(event, detail = {}) {
  const payload = {
    ...detail,
    sessionId: state.sessionId,
    pendingChoices: state.pendingChoices.length,
    revealed: state.choicesRevealed,
    choicesAreaDisplay: els.choicesArea ? getComputedStyle(els.choicesArea).display : "",
  };
  console.debug("[TRPG-CHOICE-DEBUG]", event, payload);
  try {
    fetch("/api/client-debug", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event, detail: payload }),
      keepalive: true,
    }).catch(() => {});
  } catch {
    /* Debug logging must never break gameplay. */
  }
}

function choiceLayoutDebug() {
  const firstCard = els.choicesList?.querySelector(".choice-card");
  if (!firstCard) return {};
  const rect = firstCard.getBoundingClientRect();
  const x = Math.round(rect.left + rect.width / 2);
  const y = Math.round(rect.top + rect.height / 2);
  const top = document.elementFromPoint(x, y);
  return {
    firstCardRect: {
      left: Math.round(rect.left),
      top: Math.round(rect.top),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
    },
    topElementAtFirstCardCenter: top ? {
      tag: top.tagName,
      id: top.id || "",
      className: String(top.className || ""),
      text: (top.textContent || "").trim().slice(0, 80),
    } : null,
    choicesAreaZIndex: els.choicesArea ? getComputedStyle(els.choicesArea).zIndex : "",
    choicesAreaPointerEvents: els.choicesArea ? getComputedStyle(els.choicesArea).pointerEvents : "",
  };
}

function ensureDiceBannerElement() {
  const existingBanner = document.querySelector("#diceBanner");
  if (existingBanner) {
    els.diceBanner = existingBanner;
    els.diceBannerText = existingBanner.querySelector("#diceBannerText") || document.querySelector("#diceBannerText");
    els.diceRollFace = existingBanner.querySelector(".dice-roll-face") || document.querySelector(".dice-roll-face");
    return;
  }

  const dialogueBox = els.dialogueBox || document.querySelector("#dialogueBox");
  if (!dialogueBox) return;
  const bottomArea = dialogueBox.closest(".gal-bottom-area") || dialogueBox.parentElement;
  if (!bottomArea) return;

  const banner = document.createElement("div");
  banner.id = "diceBanner";
  banner.className = "gal-dice-banner";
  banner.style.display = "none";
  banner.setAttribute("aria-live", "polite");

  const face = document.createElement("span");
  face.className = "dice-roll-face";
  face.textContent = "?";
  banner.appendChild(face);

  const text = document.createElement("span");
  text.id = "diceBannerText";
  text.className = "dice-banner-text";
  text.textContent = "判定中...";
  banner.appendChild(text);

  bottomArea.insertBefore(banner, dialogueBox);
  els.diceBanner = banner;
  els.diceBannerText = text;
  els.diceRollFace = face;
}

/* ═══════════════════════════════════════════════════
   INIT
   ═══════════════════════════════════════════════════ */

async function init() {
  ensureDiceBannerElement();
  restoreGmMode();
  await loadConfig();
  await loadScenarios();
  await resumeSessionFromUrl();
}

async function resumeSessionFromUrl() {
  const sessionId = new URLSearchParams(window.location.search).get("session");
  if (!sessionId || !/^[a-f0-9]{32}$/i.test(sessionId)) return;
  try {
    const session = await fetchJson(`/api/sessions/${sessionId}`);
    els.startScreen.style.display = "none";
    els.gameScreen.style.display = "";
    renderSession(session);
  } catch (error) {
    if (els.backendStatus) els.backendStatus.textContent = `存档读取失败: ${error.message}`;
  }
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
      .map((s) => `<option value="${escapeHtml(s.filename)}">${escapeHtml(scenarioOptionLabel(s, scenarios))}</option>`)
      .join("");
    const preferred = scenarios.find((s) => s.filename === "dragon_rpg_hybrid.json")
      || scenarios.find((s) => s.filename === "dragon_rpg.json")
      || scenarios[0];
    if (preferred) {
      els.scenarioSelect.value = preferred.filename;
      await onScenarioChange();
    }
    els.scenarioSelect.addEventListener("change", onScenarioChange);
  } catch (err) {
    els.backendStatus.textContent = `シナリオの読み込みに失敗しました: ${err.message}`;
  }
}

function scenarioOptionLabel(scenario, scenarios) {
  const filename = scenario.filename || "";
  const title = scenario.title || filename;
  if (filename.endsWith("_hybrid.json")) return `${title}（Hybrid）`;
  const hybridFilename = filename.replace(/\.json$/i, "_hybrid.json");
  if (scenarios.some((item) => item.filename === hybridFilename)) return `${title}（Base）`;
  return title;
}

async function onScenarioChange() {
  const filename = els.scenarioSelect.value;
  if (!filename) return;
  try {
    const data = await fetchJson(`/api/scenarios/${encodeURIComponent(filename)}`);
    const characters = (data.scenario?.characters || []).filter((char) => char.selectable !== false);
    state.scenarioPath = `host/prompt/processed/${filename}`;
    state.expandedCharacterId = "";
    renderCharacterCards(characters);
  } catch (err) {
    els.characterCards.innerHTML = `<p class="start-backend">キャラクターの読み込みに失敗しました</p>`;
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
    els.characterCards.innerHTML = `<p class="start-backend">このシナリオにキャラクター定義がありません</p>`;
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
    els.genderSection.style.display = "";
    updateHeroImage(char);
  } else {
    els.genderSection.style.display = "none";
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
  const backend = els.backendSelect ? els.backendSelect.value : "gemini";
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
    window.history.replaceState({}, "", `/?session=${encodeURIComponent(session.id)}`);
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
  state.choiceStack = [];
  state.choicesRevealed = false;
  state.lastDiceLogLength = 0;
  state.lastDiceSignature = "";
  state.nextDiceDc = 0;
  state.nextDiceType = "1d20";
  state.combatTargetId = "";
  state.combatActionTab = "attack";
  state.combatBusy = false;
  window.history.replaceState({}, "", "/");
  stopDiceRollAnimation();
  hideDiceBanner();
  els.gameScreen.style.display = "none";
  els.startScreen.style.display = "";
  if (els.endingOverlay) els.endingOverlay.style.display = "none";
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
  hideDiceBanner();
  setBusy(true);
  try {
    const body = { text };
    const response = await fetch(`/api/sessions/${state.sessionId}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok || !response.body) {
      throw new Error(await response.text());
    }
    renderSession(await response.json());
  } catch (error) {
    stopDiceRollAnimation();
    addMessage("assistant", "GM", `エラー: ${error.message}`);
  } finally {
    setBusy(false);
  }
}

async function submitChoice(choiceText, actionId = "") {
  choiceDebug("submit-choice-start", { choiceText, actionId });
  if (!choiceText || !state.sessionId) return;
  addMessage("user", "プレイヤー", choiceText);
  hideChoices();
  clearPendingChoices();
  hideDiceBanner();
  setBusy(true);
  try {
    const body = { text: choiceText };
    if (actionId) body.action_id = actionId;
    const response = await fetch(`/api/sessions/${state.sessionId}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) {
      throw new Error(await response.text());
    }
    renderSession(await response.json());
  } catch (error) {
    choiceDebug("submit-choice-error", { choiceText, error: error.message });
    stopDiceRollAnimation();
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
  if (els.input) els.input.placeholder = session.free_input_hint || "行動や台詞を自由に入力してください";
  state.nextDiceDc = Number(session.next_dice_dc || 0);
  state.nextDiceType = session.next_dice_type || "1d20";
  state.character = session.character || null;
  const character = session.character;

  /* Scene */
  if (els.sceneTitle) {
    els.sceneTitle.textContent = session.current_location_title || session.current_scene_title || session.current_location || session.current_scene || session.scenario_title || "開始";
    els.sceneTitle.title = session.current_scene_title && session.current_location_title !== session.current_scene_title
      ? session.current_scene_title
      : "";
  }

  if (els.background) {
    const backgroundImage = session.location_background_image || character.background_image;
    if (backgroundImage) {
      els.background.style.backgroundImage = `url(${backgroundImage})`;
    } else {
      els.background.style.backgroundImage = "";
    }
  }

  renderScenePortraits(session, character);

  /* Character info */
  if (els.characterName) els.characterName.textContent = character.name || "冒険者";
  if (els.characterDescription) els.characterDescription.textContent = character.description || "";
  renderCharacterAttributes(character.attributes || {});
  if (els.companionInfo) {
    const companion = session.companion;
    els.companionInfo.hidden = !companion;
    els.companionInfo.innerHTML = companion
      ? `${companion.image ? `<img src="${escapeAttr(companion.image)}" alt="" />` : ""}<span>同行者　${escapeHtml(companion.name || companion.id || "不明")}</span>`
      : "";
  }

  /* Meters */
  renderMeter("hp", character);
  renderMeter("mp", character);
  renderMeter("sp", character);
  els.goldText.textContent = Number(character.gold || 0).toLocaleString("ja-JP");

  /* Inventory (item objects) */
  renderInventory(character.inventory || []);
  renderEnemies(session.enemies || []);
  renderCombat(session);
  renderEnding(session.game_over);

  /* Dice log */
  renderLatestDiceResult(session.dice_log || []);
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
  els.dialogueBox.classList.toggle("no-narration", session.last_turn_narrated === false);
  if (session.last_turn_narrated === false) {
    if (els.speakerName) els.speakerName.textContent = "";
    if (els.messageText) els.messageText.textContent = "";
  }

  /* Choices */
  setPendingChoices(
    session.in_combat ? [] : (session.choices || []),
    session.last_turn_narrated === false,
  );
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
   DICE FEEDBACK
   ═══════════════════════════════════════════════════ */

function stopDiceRollAnimation() {
  if (state.diceAnimationTimer) {
    window.clearInterval(state.diceAnimationTimer);
    state.diceAnimationTimer = null;
  }
  if (els.diceBanner) els.diceBanner.classList.remove("rolling");
}

function hideDiceBanner() {
  if (els.diceBanner) els.diceBanner.style.display = "none";
}

function renderLatestDiceResult(diceLog) {
  if (!Array.isArray(diceLog) || !diceLog.length) {
    state.lastDiceLogLength = 0;
    state.lastDiceSignature = "";
    return;
  }
  const latest = diceLog[diceLog.length - 1];
  const signature = diceSignature(latest);
  const hasNewRoll = diceLog.length !== state.lastDiceLogLength || signature !== state.lastDiceSignature;
  state.lastDiceLogLength = diceLog.length;
  state.lastDiceSignature = signature;
  if (!hasNewRoll) return;
  if (isCheckRoll(latest)) {
    showDiceResult(latest);
  }
}

function diceSignature(roll) {
  if (!roll || typeof roll !== "object") return "";
  const rolls = Array.isArray(roll.rolls) ? roll.rolls.join(",") : "";
  return [roll.expression || "", rolls, roll.total ?? "", roll.dc ?? "", roll.success ?? ""].join("|");
}

function isCheckRoll(roll) {
  return Number(roll?.dc || 0) > 0;
}

function showDiceResult(roll) {
  if (!els.diceBanner || !els.diceRollFace || !els.diceBannerText || !roll) return;
  stopDiceRollAnimation();
  const rolls = Array.isArray(roll.rolls) ? roll.rolls : [];
  const total = Number(roll.total ?? 0);
  const dc = Number(roll.dc ?? 0);
  const hasCheck = dc > 0;
  const success = !roll.critical_failure && (roll.success === true || (hasCheck && total >= dc));
  els.diceBanner.style.display = "";
  els.diceBanner.classList.toggle("success", hasCheck && success);
  els.diceBanner.classList.toggle("failure", hasCheck && !success);
  els.diceBanner.classList.toggle("neutral", !hasCheck);
  els.diceRollFace.textContent = String(total);

  const parts = [`${roll.expression || "判定"}: ${rolls.join(" + ") || total}`];
  if (typeof roll.attr_mod === "number" && roll.attr_mod !== 0) {
    const sign = roll.attr_mod > 0 ? "+" : "";
    parts.push(`${sign}${roll.attr_mod}`);
  }
  parts.push(`= ${total}`);
  if (hasCheck) {
    parts.push(` / DC${dc}`);
    if (roll.critical_success) parts.push("大成功");
    else if (roll.critical_failure) parts.push("大失敗");
    else parts.push(success ? "成功" : "失敗");
  }
  els.diceBannerText.textContent = parts.join(" ");
}

/* ═══════════════════════════════════════════════════
   CHOICES
   ═══════════════════════════════════════════════════ */

function renderChoices(choices) {
  choiceDebug("render-choices-start", {
    count: Array.isArray(choices) ? choices.length : 0,
    choices: Array.isArray(choices) ? choices.map((choice) => ({
      text: typeof choice === "string" ? choice : (choice.text || ""),
      risk: typeof choice === "object" ? (choice.risk || "") : "",
      enabled: typeof choice === "object" && choice.enabled === false ? false : true,
      disabledReason: typeof choice === "object" ? (choice.disabled_reason || "") : "",
      hasChildren: typeof choice === "object" && Array.isArray(choice.children) && choice.children.length > 0,
    })) : [],
  });
  if (!choices || !choices.length) {
    hideChoices();
    return;
  }

  els.choicesList.innerHTML = "";
  const hasParentStack = state.choiceStack.length > 0;

  if (hasParentStack) {
    const backCard = document.createElement("button");
    backCard.type = "button";
    backCard.className = "choice-card choice-back";
    backCard.dataset.choiceIndex = "-1";
    backCard.dataset.choiceText = "__back__";
    const numberDiv = document.createElement("div");
    numberDiv.className = "choice-number";
    numberDiv.innerHTML = "&#9664;";
    const textDiv = document.createElement("div");
    textDiv.className = "choice-text";
    textDiv.textContent = "戻る";
    const bodyDiv = document.createElement("div");
    bodyDiv.className = "choice-body";
    bodyDiv.appendChild(textDiv);
    backCard.appendChild(numberDiv);
    backCard.appendChild(bodyDiv);
    els.choicesList.append(backCard);
  }

  for (let i = 0; i < choices.length; i++) {
    const choice = choices[i];
    const text = typeof choice === "string" ? choice : (choice.text || "");
    const preview = typeof choice === "object" ? (choice.preview || "") : "";
    const risk = typeof choice === "object" ? (choice.risk || "") : "";
    const enabled = typeof choice === "object" && choice.enabled === false ? false : true;
    const disabledReason = typeof choice === "object" ? (choice.disabled_reason || "") : "";
    const hasChildren = typeof choice === "object" && Array.isArray(choice.children) && choice.children.length > 0;

    const card = document.createElement("button");
    card.type = "button";
    card.disabled = !enabled;
    card.dataset.choiceIndex = String(i);
    card.dataset.choiceText = text;
    card.dataset.actionId = typeof choice === "object" ? (choice.action_id || choice.id || "") : "";
    if (hasChildren) {
      card.dataset.choiceParent = "true";
      card.className = `choice-card choice-group ${enabled ? "" : "disabled-choice"}`;
    } else {
      card.className = `choice-card ${isCombatChoice(text, preview, risk) ? "combat-choice" : ""} ${enabled ? "" : "disabled-choice"}`;
    }

    const riskClass = classifyRisk(risk);

    const numberDiv = document.createElement("div");
    numberDiv.className = "choice-number";
    numberDiv.textContent = String(i + 1);

    const textDiv = document.createElement("div");
    textDiv.className = "choice-text";
    textDiv.textContent = text;

    const bodyDiv = document.createElement("div");
    bodyDiv.className = "choice-body";
    bodyDiv.appendChild(textDiv);

    if (hasChildren) {
      const hintSpan = document.createElement("span");
      hintSpan.className = "choice-group-hint";
      hintSpan.textContent = Array.isArray(choice.children) ? `${choice.children.length}件` : "";
      bodyDiv.appendChild(hintSpan);
    } else if (preview) {
      const previewDiv = document.createElement("div");
      previewDiv.className = "choice-preview";
      previewDiv.textContent = preview;
      bodyDiv.appendChild(previewDiv);
    }
    if (risk && !hasChildren) {
      const riskSpan = document.createElement("span");
      riskSpan.className = `choice-risk ${riskClass}`;
      riskSpan.textContent = risk;
      bodyDiv.appendChild(riskSpan);
    }
    if (disabledReason) {
      const reasonSpan = document.createElement("span");
      reasonSpan.className = "choice-disabled-reason";
      reasonSpan.textContent = disabledReason;
      bodyDiv.appendChild(reasonSpan);
    }

    card.appendChild(numberDiv);
    card.appendChild(bodyDiv);

    els.choicesList.append(card);
  }

  els.choicesArea.style.display = "";
  els.dialogueBox.classList.remove("choices-ready");
  if (els.clickIndicator) els.clickIndicator.style.display = "none";
  choiceDebug("render-choices-visible", choiceLayoutDebug());
}

function isCombatChoice(text, preview, risk) {
  const source = `${text} ${preview} ${risk}`;
  return /攻撃|防御|回避|撤退|戦闘|敵|斬|剣|魔法|回復|ダメージ|1d20|DC\d+/i.test(source);
}

function hideChoices() {
  els.choicesArea.style.display = "none";
  els.choicesList.innerHTML = "";
}

function setPendingChoices(choices, revealImmediately = false) {
  state.pendingChoices = Array.isArray(choices) ? choices : [];
  state.choiceStack = [];
  state.choicesRevealed = false;
  hideChoices();
  if (revealImmediately && state.pendingChoices.length) {
    state.choicesRevealed = true;
    renderChoices(state.pendingChoices);
    return;
  }
  updateDialogueAdvanceState();
}

function renderScenePortraits(session, character) {
  if (!els.spriteLayer) return;
  const playerImage = session.player_portrait_image || character.character_image || "";
  const npcImage = session.dialogue_portrait_image || "";
  const locationNpcs = Array.isArray(session.location_npc_portraits)
    ? session.location_npc_portraits.filter((npc) => npc && npc.image)
    : [];
  const dialogueActive = Boolean(session.dialogue_active && playerImage && npcImage);
  els.spriteLayer.classList.toggle("dialogue-mode", dialogueActive);
  els.spriteLayer.classList.toggle("ensemble-mode", !dialogueActive && locationNpcs.length > 0);
  els.spriteLayer.classList.toggle("solo-mode", !dialogueActive && locationNpcs.length === 0 && Boolean(playerImage));

  els.locationPortraits.innerHTML = dialogueActive ? "" : locationNpcs.map((npc) => (
    `<figure class="location-portrait"><img src="${escapeAttr(npc.image)}" alt="" /><figcaption>${escapeHtml(npc.name || "")}</figcaption></figure>`
  )).join("");
  els.locationPortraits.dataset.count = String(locationNpcs.length);
  els.locationPortraits.style.display = !dialogueActive && locationNpcs.length ? "" : "none";

  els.playerPortrait.src = playerImage;
  els.playerPortrait.style.display = dialogueActive || (!locationNpcs.length && playerImage) ? "" : "none";
  els.npcPortrait.src = npcImage;
  els.npcPortrait.style.display = dialogueActive ? "" : "none";
}

function renderCharacterAttributes(attributes) {
  if (!els.characterAttributes) return;
  const labels = {
    str: "STR", dex: "DEX", int: "INT", wis: "WIS",
    end: "END", agi: "AGI", cha: "CHA", char: "CHA",
  };
  const entries = Object.entries(attributes || {}).filter(([key]) => labels[key]);
  els.characterAttributes.innerHTML = entries.length
    ? entries.map(([key, value]) => `<div><span>${labels[key]}</span><strong>${Number(value || 0)}</strong></div>`).join("")
    : '<p class="empty-attributes">能力値なし</p>';
}

function renderEnding(gameOver) {
  if (!els.endingOverlay) return;
  if (!gameOver) {
    els.endingOverlay.style.display = "none";
    return;
  }
  els.endingTitle.textContent = gameOver.title || "敗北";
  const endingLabel = document.querySelector("#endingLabel");
  if (endingLabel) endingLabel.textContent = gameOver.ending === "ignis_defeated" ? "ADVENTURE COMPLETE" : "GAME OVER";
  els.endingReason.textContent = gameOver.reason || "物語はここで終わりました。";
  els.endingOverlay.style.display = "";
}

function clearPendingChoices() {
  state.pendingChoices = [];
  state.choiceStack = [];
  state.choicesRevealed = false;
  updateDialogueAdvanceState();
}

function revealPendingChoices() {
  choiceDebug("reveal-choices", {
    blocked: state.choicesRevealed || !state.pendingChoices.length,
  });
  if (state.choicesRevealed || !state.pendingChoices.length) return;
  state.choicesRevealed = true;
  renderChoices(state.pendingChoices);
}

function handleChoiceListClick(event) {
  const card = event.target.closest(".choice-card");
  choiceDebug("choice-click", {
    targetTag: event.target?.tagName || "",
    targetClass: String(event.target?.className || ""),
    hasCard: Boolean(card),
    cardDisabled: Boolean(card?.disabled),
    cardIndex: card?.dataset.choiceIndex || "",
    cardText: card?.dataset.choiceText || "",
    cardParent: card?.dataset.choiceParent || "",
    actionId: card?.dataset.actionId || "",
    layout: choiceLayoutDebug(),
  });
  if (!card || !els.choicesList.contains(card) || card.disabled) return;

  if (card.dataset.choiceText === "__back__") {
    if (state.choiceStack.length > 0) {
      const previous = state.choiceStack.pop();
      state.pendingChoices = previous;
      state.choicesRevealed = true;
      renderChoices(state.pendingChoices);
    }
    return;
  }

  const index = Number.parseInt(card.dataset.choiceIndex || "", 10);
  const choice = Number.isInteger(index) ? state.pendingChoices[index] : null;
  if (!choice || typeof choice !== "object") return;

  const hasChildren = Array.isArray(choice.children) && choice.children.length > 0;
  if (hasChildren) {
    state.choiceStack.push(state.pendingChoices);
    state.pendingChoices = choice.children;
    state.choicesRevealed = true;
    renderChoices(state.pendingChoices);
    return;
  }

  const text = card.dataset.choiceText || (typeof choice === "string" ? choice : (choice && typeof choice === "object" ? choice.text : ""));
  if (text) submitChoice(text, card.dataset.actionId || "");
}

function renderCombat(session) {
  const combat = session.combat;
  const active = Boolean(session.in_combat && combat && combat.status);
  els.gameScreen.classList.toggle("combat-active", active);
  if (!active) {
    els.combatScreen.style.display = "none";
    if (els.combatIntro) els.combatIntro.style.display = "none";
    state.combatTargetId = "";
    return;
  }

  els.combatScreen.style.display = "";
  renderCombatIntro(combat);
  els.combatScreen.classList.toggle("busy", state.combatBusy);
  const enemies = Array.isArray(combat.enemies) ? combat.enemies : [];
  const alive = enemies.filter((enemy) => Number(enemy.hp || 0) > 0);
  if (!alive.some((enemy) => enemy.id === state.combatTargetId)) {
    state.combatTargetId = alive[0]?.id || "";
  }
  els.combatTitle.textContent = enemies.length
    ? `VS ${enemies.map((enemy) => enemy.name || enemy.id).join(" / ")}`
    : "戦闘";
  els.combatRound.textContent = String(combat.round || 1);
  els.combatPlayerName.textContent = session.character?.name || "冒険者";
  const playerImage = session.player_portrait_image || session.character?.character_image || "";
  els.combatPlayerImage.src = playerImage;
  els.combatPlayerImage.style.display = playerImage ? "" : "none";
  setCombatResource("PlayerHp", session.character, "hp");
  setCombatResource("PlayerMp", session.character, "mp");
  setCombatResource("PlayerSp", session.character, "sp");

  els.combatEnemies.classList.toggle("many-enemies", enemies.length >= 3);
  els.combatEnemies.innerHTML = enemies.map((enemy) => {
    const hp = Number(enemy.hp || 0);
    const maxHp = Math.max(1, Number(enemy.max_hp || hp || 1));
    const percent = Math.max(0, Math.min(100, (hp / maxHp) * 100));
    const selected = enemy.id === state.combatTargetId;
    const enemyImage = enemy.image
      ? `<img class="combat-enemy-image" src="${escapeAttr(enemy.image)}" alt="" />`
      : "";
    return `<button type="button" class="combat-enemy ${selected ? "selected" : ""} ${hp <= 0 ? "defeated" : ""}"
      data-combat-target="${escapeAttr(enemy.id || "")}" ${hp <= 0 ? "disabled" : ""}>
      ${enemyImage}
      <span class="combatant-side">ENEMY</span>
      <h3>${escapeHtml(enemy.name || enemy.id || "敵")}</h3>
      <div class="combat-resource hp"><span>HP</span><i><b style="width:${percent}%"></b></i><strong>${hp}/${maxHp}</strong></div>
      ${enemy.description ? `<p>${escapeHtml(enemy.description)}</p>` : ""}
      ${renderAbilityTags(enemy.skills || [], true)}
    </button>`;
  }).join("");

  const logs = Array.isArray(combat.log) ? combat.log : [];
  els.combatLog.innerHTML = logs.length
    ? logs.map((entry) => `<div class="combat-log-entry ${escapeAttr(entry.kind || "")}"><strong>R${entry.round || 1}</strong><span>${escapeHtml(entry.text || "")}</span></div>`).join("")
    : '<div class="combat-log-entry"><strong>R1</strong><span>行動を選択してください。</span></div>';
  els.combatLog.scrollTop = els.combatLog.scrollHeight;

  const terminal = combat.status !== "active";
  els.combatScreen.classList.toggle("combat-terminal", terminal);
  els.combatScreen.classList.toggle("combat-defeat", combat.status === "defeat");
  els.combatScreen.classList.toggle("combat-victory", combat.status === "victory");
  els.combatResult.style.display = terminal ? "" : "none";
  els.combatActionTabs.style.display = terminal ? "none" : "";
  els.combatActions.style.display = terminal ? "none" : "grid";
  if (terminal) {
    const labels = { victory: "勝利", defeat: "敗北", fled: "撤退成功" };
    els.combatResultTitle.textContent = labels[combat.status] || "戦闘終了";
    els.combatResultText.textContent = combat.result?.summary || "戦闘結果が確定しました。";
    els.combatResolveButton.disabled = state.combatBusy || !combat.pending_resolution;
  } else {
    state.combatActions = Array.isArray(combat.actions) ? combat.actions : [];
    renderCombatActions(state.combatActions);
  }
}

function setCombatResource(suffix, actor, stat) {
  const value = Number(actor?.[stat] || 0);
  const max = Math.max(1, Number(actor?.[`max_${stat}`] || value || 1));
  els[`combat${suffix}`].textContent = `${value}/${max}`;
  els[`combat${suffix}Bar`].style.width = `${Math.max(0, Math.min(100, (value / max) * 100))}%`;
}

function renderCombatActions(actions) {
  const groups = [
    { id: "attack", label: "攻撃", types: ["attack"] },
    { id: "skill", label: "技能", types: ["skill"] },
    { id: "item", label: "道具", types: ["item"] },
    { id: "tactics", label: "戦術", types: ["defend", "flee"] },
  ].filter((group) => actions.some((action) => group.types.includes(action.type)));
  if (!groups.some((group) => group.id === state.combatActionTab)) {
    state.combatActionTab = groups[0]?.id || "attack";
  }
  els.combatActionTabs.innerHTML = groups.map((group) => `<button type="button" class="combat-tab ${group.id === state.combatActionTab ? "active" : ""}" data-combat-tab="${group.id}">${group.label}</button>`).join("");
  const current = groups.find((group) => group.id === state.combatActionTab);
  const visible = current ? actions.filter((action) => current.types.includes(action.type)) : [];
  els.combatActions.innerHTML = visible.map((action) => {
    const cost = action.cost ? `${String(action.cost_type || "").toUpperCase()} ${action.cost}` : "";
    const description = action.enabled === false ? (action.disabled_reason || "使用できません") : (action.description || "");
    return `<button type="button" class="combat-action" data-combat-action-type="${escapeAttr(action.type || "")}" data-combat-action-id="${escapeAttr(action.id || "")}" ${action.enabled === false ? "disabled" : ""}>
      <strong>${escapeHtml(action.name || action.id || "行動")}</strong>
      ${cost ? `<em>${escapeHtml(cost)}</em>` : ""}
      ${renderAbilityTags([action])}
      <span>${escapeHtml(description)}</span>
    </button>`;
  }).join("");
}

function renderCombatIntro(combat) {
  if (!els.combatIntro || !els.combatIntroText || !els.combatIntroContinue) return;
  const combatId = String(combat?.id || "");
  const introText = String(combat?.intro_text || "").trim();
  const visible = Boolean(combatId && introText && combat?.status === "active" && state.combatIntroSeenId !== combatId);
  els.combatIntro.dataset.combatId = combatId;
  els.combatIntroText.textContent = introText;
  els.combatIntro.style.display = visible ? "" : "none";
  els.combatScreen.classList.toggle("intro-active", visible);
}

function renderAbilityTags(abilities, compact = false) {
  const tags = [];
  for (const ability of abilities || []) {
    if (!ability || typeof ability !== "object") continue;
    if (ability.damage) tags.push(`威力 ${ability.damage}`);
    if (ability.healing) tags.push(`回復 ${ability.healing}`);
    if (ability.accuracy !== undefined) tags.push(`命中 ${ability.accuracy}%`);
    if (ability.element) tags.push(String(ability.element).toUpperCase());
    if (ability.all_targets) tags.push("全体");
    if (ability.hits_per_element) tags.push(`${ability.hits_per_element}回×${(ability.multi_elements || []).length || 1}属性`);
    if (ability.check?.dc) tags.push(`判定 DC${ability.check.dc}`);
    for (const followup of ability.followups || []) {
      if (followup?.damage) tags.push(`追撃 ${followup.damage}`);
      if (followup?.element) tags.push(`追撃 ${String(followup.element).toUpperCase()}`);
    }
    if (compact && ability.name) tags.unshift(ability.name);
  }
  if (!tags.length) return "";
  return `<div class="combat-effect-tags">${tags.slice(0, compact ? 4 : 6).map((tag) => `<i>${escapeHtml(tag)}</i>`).join("")}</div>`;
}

async function submitCombatAction(actionType, actionId) {
  if (!state.sessionId || state.combatBusy) return;
  state.combatBusy = true;
  els.combatScreen.classList.add("busy");
  try {
    const session = await fetchJson(`/api/sessions/${state.sessionId}/combat/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_type: actionType, action_id: actionId, target_id: state.combatTargetId }),
    });
    state.combatBusy = false;
    renderSession(session);
  } catch (error) {
    const errorEntry = document.createElement("div");
    errorEntry.className = "combat-log-entry error";
    errorEntry.innerHTML = `<strong>ERROR</strong><span>${escapeHtml(error.message)}</span>`;
    els.combatLog.append(errorEntry);
    els.combatLog.scrollTop = els.combatLog.scrollHeight;
  } finally {
    state.combatBusy = false;
    els.combatScreen.classList.remove("busy");
  }
}

async function resolveCombatResult() {
  if (!state.sessionId || state.combatBusy) return;
  state.combatBusy = true;
  els.combatScreen.classList.add("busy");
  els.combatResultText.textContent = "戦闘終了を処理しています…";
  try {
    const session = await fetchJson(`/api/sessions/${state.sessionId}/combat/resolve`, { method: "POST" });
    state.combatBusy = false;
    renderSession(session);
  } catch (error) {
    els.combatResultText.textContent = `結果処理エラー: ${error.message}`;
  } finally {
    state.combatBusy = false;
    els.combatScreen.classList.remove("busy");
  }
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
if (els.endingRestartButton) els.endingRestartButton.addEventListener("click", newSession);
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
if (els.choicesList) els.choicesList.addEventListener("click", handleChoiceListClick);
if (els.combatScreen) {
  els.combatScreen.addEventListener("click", (event) => {
    const target = event.target.closest("[data-combat-target]");
    if (target && !target.disabled) {
      state.combatTargetId = target.dataset.combatTarget || "";
      els.combatEnemies.querySelectorAll(".combat-enemy").forEach((enemy) => {
        enemy.classList.toggle("selected", enemy.dataset.combatTarget === state.combatTargetId);
      });
      return;
    }
    const tab = event.target.closest("[data-combat-tab]");
    if (tab) {
      state.combatActionTab = tab.dataset.combatTab || "attack";
      renderCombatActions(state.combatActions);
      return;
    }
    const action = event.target.closest("[data-combat-action-type]");
    if (action && !action.disabled) {
      submitCombatAction(action.dataset.combatActionType || "", action.dataset.combatActionId || "");
    }
  });
}
if (els.combatResolveButton) els.combatResolveButton.addEventListener("click", resolveCombatResult);
if (els.combatIntroContinue) {
  els.combatIntroContinue.addEventListener("click", () => {
    state.combatIntroSeenId = els.combatIntro?.dataset.combatId || "";
    if (els.combatIntro) els.combatIntro.style.display = "none";
    if (els.combatScreen) els.combatScreen.classList.remove("intro-active");
  });
}
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
