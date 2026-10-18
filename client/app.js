/* ═══════════════════════════════════════════════════
   Local TRPG — Client Application
   ═══════════════════════════════════════════════════ */

const state = {
  sessionId: null,
  pendingChoices: [],
  choiceStack: [],
  choicePortrait: null,
  choicesRevealed: false,
  selectedCharacterId: "hero",
  selectedCharacterImage: "/static/images/char_male_hero_v2.png",
  selectedCharacter: null,
  characters: [],
  scenarioPath: "host/prompt/processed/dragon_rpg_hybrid.json",
  lastDiceLogLength: 0,
  lastDiceSignature: "",
  diceAnimationTimer: null,
  pendingCheck: null,
  dicePresentation: null,
  nextDiceDc: 0,
  nextDiceType: "1d20",
  character: null,
  combatTargetId: "",
  combatActionTab: "attack",
  combatBusy: false,
  combatPlayback: null,
  combatActions: [],
  combatTutorial: null,
  combatIntroSeenId: "",
  combatLogId: "",
  combatLogExpanded: false,
  session: null,
  serviceBusy: false,
  turnBusy: false,
  shop: null,
  shopTab: "buy",
  shopItemId: "",
  shopQuantity: 1,
  shopEventId: "",
  questLogIds: new Set(),
};

/* ── DOM References ── */
const els = {
  /* Start screen */
  startScreen:     document.querySelector("#startScreen"),
  startTitle:      document.querySelector("#startTitle"),
  startError:      document.querySelector("#startError"),
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
  diceCheckCard:   document.querySelector("#diceCheckCard"),
  diceCheckBackdrop: document.querySelector("#diceCheckBackdrop"),
  diceCheckTitle:  document.querySelector("#diceCheckTitle"),
  diceCheckSummary: document.querySelector("#diceCheckSummary"),
  diceCheckFormula: document.querySelector("#diceCheckFormula"),
  diceCheckAdvantage: document.querySelector("#diceCheckAdvantage"),
  diceCheckCrucial: document.querySelector("#diceCheckCrucial"),
  diceCheckActions: document.querySelector("#diceCheckActions"),
  diceCheckRoll:   document.querySelector("#diceCheckRoll"),
  diceCheckCancel: document.querySelector("#diceCheckCancel"),
  diceCheckAnimation: document.querySelector("#diceCheckAnimation"),
  diceNatural:     document.querySelector("#diceNatural"),
  diceFirst:       document.querySelector("#diceFirst"),
  diceSecond:      document.querySelector("#diceSecond"),
  diceNaturalSecond: document.querySelector("#diceNaturalSecond"),
  diceCalculation: document.querySelector("#diceCalculation"),
  diceOutcome:     document.querySelector("#diceOutcome"),
  diceCritical:    document.querySelector("#diceCritical"),
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
  choiceDescription: document.querySelector("#choiceDescription"),
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
  combatLogToggle: document.querySelector("#combatLogToggle"),
  combatActionTabs: document.querySelector("#combatActionTabs"),
  combatTutorial: document.querySelector("#combatTutorial"),
  combatActions: document.querySelector("#combatActions"),
  combatResult: document.querySelector("#combatResult"),
  combatResultTitle: document.querySelector("#combatResultTitle"),
  combatResultText: document.querySelector("#combatResultText"),
  combatResolveButton: document.querySelector("#combatResolveButton"),
  endingOverlay: document.querySelector("#endingOverlay"),
  endingTitle: document.querySelector("#endingTitle"),
  endingReason: document.querySelector("#endingReason"),
  endingRestartButton: document.querySelector("#endingRestartButton"),
  endingRetryButton: document.querySelector("#endingRetryButton"),
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
    showStartError(`シナリオの読み込みに失敗しました: ${err.message}`);
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
    els.startTitle.textContent = data.scenario?.meta?.title || els.scenarioSelect.selectedOptions[0].textContent;
    document.title = `${els.startTitle.textContent} — AI GM TRPG`;
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
    els.heroNameInput.value = "";
    els.characterCards.innerHTML = `<p class="start-backend">このシナリオにキャラクター定義がありません</p>`;
    return;
  }
  const selectedId = characters.some((char) => char.id === state.selectedCharacterId)
    ? state.selectedCharacterId
    : characters[0].id;
  els.characterCards.innerHTML = characters.map((char) => {
    const isSelected = char.id === selectedId;
    const description = (char.description || "").match(/[^。]+。?/)?.[0] || "";
    return `<button class="char-card ${isSelected ? "selected" : ""}" data-char-id="${escapeAttr(char.id)}" type="button" aria-pressed="${isSelected}">
      <div class="char-card-portrait"><img class="char-card-img" src="${escapeAttr(characterPortrait(char))}" alt="" /></div>
      <div class="char-card-info">
        <strong>${escapeHtml(char.name || char.id)}</strong>
        <p class="char-card-desc" title="${escapeAttr(char.description || "")}">${escapeHtml(description)}</p>
        <span class="char-card-stats">HP ${char.hp} / MP ${char.mp}</span>
      </div>
    </button>`;
  }).join("");

  document.querySelectorAll(".char-card").forEach((card) => {
    card.addEventListener("click", () => {
      const charId = card.dataset.charId;
      const char = characters.find((c) => c.id === charId);
      if (char) selectCharacter(char);
    });
  });
  const selected = characters.find((char) => char.id === selectedId) || characters[0];
  selectCharacter(selected);
}

function selectCharacter(char) {
  state.selectedCharacterId = char.id;
  state.selectedCharacter = char;
  els.heroNameInput.value = char.default_name || char.name || "";
  state.selectedCharacterImage = characterPortrait(char);
  // Only classes with a female portrait (the hero) offer the gender choice.
  if (els.genderSection) els.genderSection.hidden = !char.image_female;
  document.querySelectorAll(".char-card").forEach((card) => {
    const selected = card.dataset.charId === char.id;
    card.classList.toggle("selected", selected);
    card.setAttribute("aria-pressed", String(selected));
  });
}

function characterPortrait(char) {
  const gender = document.querySelector('input[name="heroGender"]:checked')?.value || "男勇者";
  return gender === "女勇者" && char.image_female
    ? char.image_female
    : char.image || "";
}

function showStartError(message) {
  els.startError.textContent = message;
  els.startError.hidden = !message;
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
  showStartError("");
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
    showStartError(`エラー: ${err.message}`);
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
  state.selectedCharacterImage = characterPortrait(char);
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
  closeDiceCheck();
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
  if (state.serviceBusy || state.turnBusy || state.pendingCheck) return;
  const text = els.input.value.trim();
  if (!text || !state.sessionId) return;
  els.input.value = "";
  await submitChoice(text);
}

async function submitChoice(choiceText, actionId = "", check = null) {
  if (state.serviceBusy || state.turnBusy || state.pendingCheck) return;
  choiceDebug("submit-choice-start", { choiceText, actionId });
  if (!choiceText || !state.sessionId) return;
  const previousChoices = {
    choices: state.pendingChoices, stack: state.choiceStack,
    portrait: state.choicePortrait, revealed: state.choicesRevealed,
  };
  addMessage("user", "プレイヤー", choiceText);
  hideChoices();
  clearPendingChoices();
  setBusy(true);
  if (check && !state.session?.in_combat) startDicePresentation(check, choiceText);
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
    await renderTurnResponse(await response.json(), choiceText);
  } catch (error) {
    choiceDebug("submit-choice-error", { choiceText, error: error.message });
    closeDiceCheck();
    addMessage("assistant", "GM", `エラー: ${error.message}`);
    state.pendingChoices = previousChoices.choices;
    state.choiceStack = previousChoices.stack;
    state.choicesRevealed = previousChoices.revealed;
    restoreChoicePortrait(previousChoices.portrait);
    if (state.choicesRevealed) {
      renderChoices(state.pendingChoices);
      els.choicesList.querySelector(".choice-card")?.focus();
    } else {
      updateDialogueAdvanceState();
    }
  } finally {
    setBusy(false);
  }
}

/* ═══════════════════════════════════════════════════
   RENDER SESSION STATE
   ═══════════════════════════════════════════════════ */

function renderSession(session) {
  const sameSession = state.session?.id === session.id;
  if (!sameSession) {
    closeShop();
    state.shopEventId = session.last_action_result?.event_id || "";
    state.questLogIds.clear();
    document.querySelector("#notifications").replaceChildren();
  }
  state.session = session;
  state.sessionId = session.id;
  renderMaps();
  if (els.input) els.input.placeholder = session.free_input_hint || "行動や台詞を自由に入力してください";
  state.nextDiceDc = Number(session.next_dice_dc || 0);
  state.nextDiceType = session.next_dice_type || "1d20";
  state.character = session.character || null;
  const character = session.character;

  /* Scene */
  if (els.sceneTitle) {
    els.sceneTitle.innerHTML = rubyHtml(session.current_location_title || session.current_scene_title || session.current_location || session.current_scene || session.scenario_title || "開始");
    els.sceneTitle.title = session.current_scene_title && session.current_location_title !== session.current_scene_title
      ? session.current_scene_title
      : "";
  }

  if (els.background) {
    const backgroundImage = session.location_background_image || character.background_image;
    if (backgroundImage) {
      els.background.style.backgroundImage = `url(${backgroundImage})`;
      els.background.dataset.placeholder = '';
      const probe = new Image();
      probe.onerror = () => {
        if (state.session?.location_background_image === backgroundImage) {
          els.background.style.backgroundImage = '';
          els.background.dataset.placeholder = session.current_location_title || '';
        }
      };
      probe.src = backgroundImage;
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
      ? `${companion.image ? `<img src="${escapeAttr(companion.image)}" alt="" />` : ""}<span>同行者　${rubyHtml(companion.name || companion.id || "不明")}${companion.description ? `<small class="companion-role">${rubyHtml(companion.description)}</small>` : ""}</span>`
      : "";
  }

  /* Meters */
  renderMeter("hp", character);
  renderMeter("mp", character);
  renderMeter("sp", character);
  els.goldText.textContent = Number(character.gold || 0).toLocaleString("ja-JP");

  /* Inventory (item objects) */
  renderInventory(character.inventory || []);
  renderQuests(session.quests || []);
  for (const entry of session.system_logs || []) {
    if (!/^クエスト(更新|達成)：/.test(entry.text)) continue;
    const key = entry.event_id || `${entry.created_at}:${entry.text}`;
    if (sameSession && !state.questLogIds.has(key)) showNotification(entry.text);
    state.questLogIds.add(key);
  }
  const shopAction = session.last_action_result || {};
  if (state.shop && (state.shop.location_id !== session.current_location || session.in_combat || session.game_over)) closeShop();
  if (sameSession && shopAction.open_shop && shopAction.event_id !== state.shopEventId && !session.in_combat && !session.game_over) {
    state.shopEventId = shopAction.event_id;
    openShop(shopAction.open_shop);
  }
  renderEnemies(session.enemies || []);
  renderCombat(session);
  renderEnding(session.game_over);

  /* Dice log */
  renderLatestDiceResult(session.dice_log || []);
  renderList(
    els.diceLog,
    (session.dice_log || []).slice(-5).reverse().map(
      (roll) => `🎲 ${roll.expression}: ${diceFacesText(roll)} = ${roll.total}`
    ),
    "判定なし",
  );

  /* System logs */
  renderList(
    els.systemLogs,
    (session.system_logs || []).slice(-8).reverse().map((entry) => entry.text),
    "ログなし",
    true,
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

function prependItemIcon(nameNode, item) {
  if (typeof item.icon !== "string" || !item.icon.trim()) return;
  const icon = document.createElement("img");
  icon.className = "item-icon";
  icon.alt = "";
  icon.width = 32;
  icon.height = 32;
  icon.addEventListener("error", () => icon.remove(), { once: true });
  icon.src = item.icon;
  nameNode.prepend(icon);
}

function renderInventory(items) {
  const slotLabels = { weapon: "武器", armor: "防具", accessory: "補助" };
  const isEquipped = item => Boolean(slotLabels[item.slot]) && (state.character?.equipment || []).some(entry =>
    (typeof entry === "string" ? entry : entry.name || entry.id) === item.name || entry === item.id);
  const expanded = new Set([...els.inventory.querySelectorAll(".expanded")].map(row => row.dataset.itemId));
  els.inventory.innerHTML = "";
  if (!items.length) {
    const li = document.createElement("li");
    li.className = "inventory-item";
    li.innerHTML = `<div class="item-header"><span class="item-name" style="color:var(--muted)">所持品なし</span></div>`;
    els.inventory.append(li);
    return;
  }
  // TODO(design): Items without category stay ungrouped until their category is specified.
  const groups = { consumable: "消耗品", equipment: "装備", material: "素材", loot: "戦利品", key: "重要", "": "" };
  for (const [category, label] of Object.entries(groups)) {
    const grouped = items.filter(item => (item.category || "") === category);
    if (!grouped.length) continue;
    if (label) {
      const heading = document.createElement("li");
      heading.className = "inventory-group";
      heading.innerHTML = `<h3>${label}</h3>`;
      els.inventory.append(heading);
    }
    for (const item of grouped) {
    const name = typeof item === "string" ? item : (item.name || "不明");
    const desc = typeof item === "object" ? (item.description || "") : "";
    const effect = typeof item === "object" ? (item.effect || "") : "";
    const qty = typeof item === "object" ? (item.quantity || 1) : 1;

    const li = document.createElement("li");
    li.className = "inventory-item";
    li.dataset.itemId = item.id || name;
    li.classList.toggle("expanded", expanded.has(li.dataset.itemId));
    const slotLabel = slotLabels[item.slot] || "";
    const equipped = isEquipped(item);
    const idle = !state.session?.in_combat && !state.session?.game_over;
    const equippable = Boolean(slotLabel) && !equipped && idle;
    const replacement = equippable ? items.find(other => other.slot === item.slot && isEquipped(other)) : null;
    const equipLabel = replacement ? `装備する（${replacement.name}と入れ替え）` : "装備する";
    const usable = (["heal", "restore", "permanent"].includes(item.combat?.kind) && idle) || equippable;

    const hasDetails = desc || effect || usable;

    li.innerHTML = `
      <div class="item-header" role="button" tabindex="0" aria-expanded="${li.classList.contains("expanded")}">
        <span class="item-name">${escapeHtml(name)}${slotLabel ? ` <span class="item-qty">${slotLabel}</span>` : ''}</span>
        <span style="display:flex;align-items:center;gap:6px">
          ${equipped ? '<span class="item-qty equipped-tag">装備中</span>' : ''}
          ${item.key_item ? '<span class="item-qty key-tag">重要</span>' : ''}
          <span class="item-qty">×${qty}</span>
          ${hasDetails ? '<span class="item-toggle">▼</span>' : ''}
        </span>
      </div>
      ${hasDetails ? `
        <div class="item-details">
          ${desc ? `<div class="item-desc">${rubyHtml(desc)}</div>` : ''}
          ${effect ? `<div class="item-effect">${rubyHtml(effect)}</div>` : ''}
          ${usable ? `<button type="button" class="start-btn item-use">${equippable ? escapeHtml(equipLabel) : "使う"}</button>` : ''}
        </div>
      ` : ''}
    `;

    prependItemIcon(li.querySelector(".item-name"), item);

    if (hasDetails) {
      const header = li.querySelector(".item-header");
      const toggle = () => header.setAttribute("aria-expanded", li.classList.toggle("expanded"));
      header.addEventListener("click", toggle);
      header.addEventListener("keydown", event => {
        if (["Enter", " "].includes(event.key)) { event.preventDefault(); toggle(); }
      });
    }
    li.querySelector(".item-use")?.addEventListener("click", () => useInventoryItem(item.id || name));

    els.inventory.append(li);
    }
  }
}

function showNotification(text) {
  const toast = document.createElement("div");
  toast.className = "notification";
  toast.textContent = text;
  document.querySelector("#notifications").append(toast);
  setTimeout(() => toast.remove(), 3000);
}

function renderQuests(quests) {
  const root = document.querySelector("#quests");
  const expanded = new Set([...root.querySelectorAll("details[open]")].map(row => row.dataset.questId));
  root.replaceChildren();
  const labels = { main: "メイン", side: "サブ", mystery: "謎" };
  for (const quest of [...quests.filter(q => q.status === "active"), ...quests.filter(q => q.status !== "active")]) {
    const ended = quest.status !== "active";
    const card = document.createElement(ended ? "details" : "article");
    card.className = `inventory-item quest-card quest-${quest.kind}`;
    card.dataset.questId = quest.id;
    if (ended) card.open = expanded.has(quest.id);
    const heading = `<span class="item-qty quest-kind">${labels[quest.kind] || ""}</span> <strong>${rubyHtml(quest.title)}</strong>
      ${ended ? `<span class="quest-${quest.status}">${quest.status === "completed" ? "達成" : "失敗"}</span>` : ""}`;
    card.innerHTML = `${ended ? `<summary>${heading}</summary>` : `<div>${heading}</div>`}
      <p class="item-desc">${rubyHtml(quest.description)}</p>
      ${quest.clue_count !== undefined ? `<p class="item-desc">手がかり：${quest.clue_count}</p>` : ""}
      ${(quest.completed_stages || []).map(text => `<p class="quest-done">${rubyHtml(text)}</p>`).join("")}
      ${quest.current_objective ? `<p>▶ ${rubyHtml(quest.current_objective)}</p>` : ""}`;
    root.append(card);
  }
}

async function serviceRequest(path, body) {
  const response = await fetch(`/api/sessions/${state.sessionId}/${path}`, body === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "この行動は現在選択できません。");
  return data;
}

async function useInventoryItem(itemId) {
  if (state.serviceBusy || state.turnBusy) return;
  state.serviceBusy = true;
  try {
    const result = await serviceRequest("items/use", { item_id: itemId });
    renderSession(result.session);
    showNotification(result.message);
  } catch (error) {
    showNotification(error.message);
  } finally {
    state.serviceBusy = false;
  }
}

function closeShop() {
  document.querySelector("#shopOverlay").style.display = "none";
  state.shop = null;
  state.shopFocus?.focus();
  state.shopFocus = null;
}

async function openShop(shopId) {
  const sessionId = state.sessionId;
  try {
    const shop = await serviceRequest(`shops/${encodeURIComponent(shopId)}`);
    if (sessionId !== state.sessionId || shop.location_id !== state.session.current_location) return;
    state.shop = shop;
    state.shopTab = "buy";
    state.shopItemId = "";
    state.shopQuantity = 1;
    state.shopFocus = document.activeElement;
    document.querySelector("#shopOverlay").style.display = "flex";
    document.querySelector("#shopLine").textContent = shop.greeting;
    renderShop();
    document.querySelector("#shopCloseBtn").focus();
  } catch (error) { showNotification(error.message); }
}

function shopLimit(item) {
  if (!item) return 0;
  if (state.shopTab === "sell") return Number(item.quantity || 0);
  if (item.enabled === false) return 0;
  return Math.min(item.stock === null ? Infinity : item.stock,
    item.price > 0 ? Math.floor(state.shop.gold / item.price) : Number.MAX_SAFE_INTEGER);
}

function renderShop() {
  const shop = state.shop;
  if (!shop) return;
  const selling = state.shopTab === "sell";
  document.querySelector("#shopTitle").textContent = shop.title;
  document.querySelector("#shopGold").textContent = Number(shop.gold).toLocaleString("ja-JP");
  const portrait = document.querySelector("#shopPortrait");
  portrait.hidden = !shop.portrait_image;
  portrait.src = shop.portrait_image || "";
  for (const [id, selected] of [["shopBuyTab", !selling], ["shopSellTab", selling]]) {
    document.querySelector(`#${id}`).setAttribute("aria-selected", selected);
    document.querySelector(`#${id}`).disabled = state.serviceBusy;
  }
  document.querySelector("#shopSellTab").disabled = !shop.buys || state.serviceBusy;
  const items = selling ? shop.sell_items : shop.items;
  if (!items.some(item => item.item_id === state.shopItemId)) state.shopItemId = items[0]?.item_id || "";
  const list = document.querySelector("#shopItems");
  list.replaceChildren();
  for (const item of items) {
    const row = document.createElement("button");
    row.type = "button";
    row.className = "inventory-item shop-row";
    row.classList.toggle("selected", item.item_id === state.shopItemId);
    row.classList.toggle("sold-out", item.stock === 0);
    row.setAttribute("aria-pressed", item.item_id === state.shopItemId);
    row.disabled = state.serviceBusy;
    row.innerHTML = `<div class="item-name">${escapeHtml(item.name)}</div><div class="item-desc shop-effect">${rubyHtml(item.effect || "")}</div>
      <div class="shop-row-bottom"><span class="shop-price ${!selling && item.price > shop.gold ? "unaffordable" : ""}">${item.price} G</span>
      <span class="item-qty">${item.stock === null ? "∞" : `${selling ? "所持：" : "在庫 "}${item.stock}`}</span>
      ${item.stock === 0 ? '<span class="item-desc">売り切れ</span>' : ""}</div>`;
    prependItemIcon(row.querySelector(".item-name"), item);
    row.addEventListener("click", () => {
      state.shopItemId = item.item_id;
      state.shopQuantity = 1;
      document.querySelector("#shopLine").textContent = shop.greeting;
      renderShop();
    });
    list.append(row);
  }
  if (!items.length) list.innerHTML = '<p class="item-desc">所持品なし</p>';
  const item = items.find(entry => entry.item_id === state.shopItemId);
  const detail = document.querySelector("#shopDetail");
  if (!item) { detail.replaceChildren(); return; }
  const limit = shopLimit(item);
  state.shopQuantity = Math.max(0, Math.min(state.shopQuantity || 1, limit));
  const owned = (state.character.inventory || []).find(entry => entry.id === item.item_id || entry.name === item.name)?.quantity || 0;
  const reason = selling ? "" : item.stock === 0 ? "売り切れ" : item.enabled === false ? item.reason : limit < 1 ? shop.poor_line : "";
  if (reason === shop.poor_line) document.querySelector("#shopLine").textContent = shop.poor_line;
  detail.innerHTML = `<h3>${escapeHtml(item.name)}</h3><p class="item-desc">${rubyHtml(item.description || "")}</p>
    <p class="item-effect">${rubyHtml(item.effect || "")}</p><p>所持：${owned}</p>
    <div class="shop-purchase"><div class="shop-quantity">
      <button type="button" class="gal-menu-btn" id="shopMinus" ${state.shopQuantity <= 1 || state.serviceBusy ? "disabled" : ""}>−</button>
      <output>${state.shopQuantity}</output>
      <button type="button" class="gal-menu-btn" id="shopPlus" ${state.shopQuantity >= limit || state.serviceBusy ? "disabled" : ""}>+</button>
      <span class="shop-price">${item.price * state.shopQuantity} G</span></div>
      <button type="button" class="start-btn" id="shopTrade" ${limit < 1 || state.serviceBusy ? "disabled" : ""}>${selling ? "売却する" : "購入する"}</button>
      <p class="item-desc">${escapeHtml(reason)}</p></div>`;
  document.querySelector("#shopMinus").onclick = () => { state.shopQuantity--; renderShop(); };
  document.querySelector("#shopPlus").onclick = () => { state.shopQuantity++; renderShop(); };
  document.querySelector("#shopTrade").onclick = performShopTrade;
}

async function performShopTrade() {
  if (!state.shop || state.serviceBusy || state.turnBusy) return;
  const shopId = state.shop.id;
  state.serviceBusy = true;
  renderShop();
  try {
    const result = await serviceRequest(`shops/${encodeURIComponent(shopId)}/${state.shopTab}`, {
      item_id: state.shopItemId, quantity: state.shopQuantity,
    });
    renderSession(result.session);
    if (state.shop?.id === shopId) {
      state.shop = result.shop;
      document.querySelector("#shopLine").textContent = result.message;
    }
  } catch (error) {
    if (state.shop?.id === shopId) document.querySelector("#shopLine").textContent = error.message;
  } finally {
    state.serviceBusy = false;
    renderShop();
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
      ${enemy.description ? `<p>${rubyHtml(enemy.description)}</p>` : ""}
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
  if (els.diceCheckCard) els.diceCheckCard.classList.remove("rolling", "settling");
}

function settleDice() {
  for (const die of [els.diceFirst, els.diceSecond]) {
    const body = window.getComputedStyle(die.querySelector(".dice-body"));
    const flight = window.getComputedStyle(die.querySelector(".dice-flight"));
    const shadow = window.getComputedStyle(die.querySelector(".dice-shadow"));
    die.style.setProperty("--dice-settle-transform", body.transform);
    die.style.setProperty("--dice-settle-flight", flight.transform);
    die.style.setProperty("--dice-settle-shadow-transform", shadow.transform);
    die.style.setProperty("--dice-settle-shadow-opacity", shadow.opacity);
  }
  stopDiceRollAnimation();
  els.diceCheckCard.classList.add("settling");
}

function openDiceCheck(choice, focus) {
  if (!choice.check || state.session?.in_combat || state.turnBusy || state.serviceBusy) return;
  state.pendingCheck = { choice, focus };
  showDiceCheckCard(choice.check, choice.text);
  els.choicesArea.style.display = "none";
  els.diceCheckActions.hidden = false;
  els.diceCheckAnimation.hidden = true;
  els.diceCheckRoll.focus();
}

function showDiceCheckCard(check, title) {
  els.diceCheckTitle.innerHTML = rubyHtml(title || "判定");
  const label = check?.skill ? `${check.skill}（${check.attribute_label}）` : check?.attribute_label || "";
  els.diceCheckSummary.textContent = check ? `${label}判定　DC ${check.dc}` : "";
  els.diceCheckFormula.textContent = check
    ? `${check.dice} ${check.modifier < 0 ? "−" : "＋"} ${Math.abs(check.modifier)}${check.attribute_label ? `（${check.attribute_label}${check.proficiency_bonus ? "＋熟練" : ""}）` : ""}`
    : "";
  showDiceAdvantage(check);
  showDiceCrucial(check);
  els.diceSecond.hidden = !check?.advantage;
  for (const die of [els.diceFirst, els.diceSecond]) die.classList.remove("selected", "discarded");
  els.diceOutcome.classList.remove("success", "failure");
  els.diceCheckSummary.hidden = !check;
  els.diceCheckFormula.hidden = !check;
  els.diceCheckCard.classList.remove("rolling", "settling", "faces-visible", "critical-success", "critical-failure", "crucial-failure", "instant-result");
  els.diceCheckCard.style.display = "";
  els.diceCheckBackdrop.hidden = false;
  els.gameScreen.classList.add("dice-active");
}

function showDiceAdvantage(check) {
  els.diceCheckAdvantage.textContent = check?.advantage
    ? `${check.advantage === "advantage" ? "有利" : "不利"}：${(check.advantage_reasons || []).join("、")}` : "";
  els.diceCheckAdvantage.hidden = !check?.advantage;
}

function showDiceCrucial(check) {
  els.diceCheckCrucial.textContent = check?.crucial
    ? (check.crucial_reason === "game_over" ? "失敗すると危険" : "失敗すると戦闘") : "";
  els.diceCheckCrucial.hidden = !check?.crucial;
}

function selectedDiceFace(roll) {
  return Number(roll.selected_roll ?? roll.rolls[0]);
}

function diceFacesText(roll) {
  return roll.advantage && roll.rolls?.length === 2
    ? `[${roll.rolls.join(", ")}] → ${selectedDiceFace(roll)}` : (roll.rolls || []).join(" + ");
}

function showDiceFaces(roll) {
  els.diceNatural.textContent = String(roll.rolls[0]);
  els.diceNatural.hidden = false;
  els.diceSecond.hidden = !(roll.advantage && roll.rolls.length === 2);
  els.diceNaturalSecond.textContent = String(roll.rolls[1] ?? "?");
  els.diceNaturalSecond.hidden = els.diceSecond.hidden;
  for (const number of [els.diceNatural, els.diceNaturalSecond]) {
    number.classList.toggle("two-digits", number.textContent.length === 2);
  }
  els.diceCheckCard.classList.add("faces-visible");
  [els.diceFirst, els.diceSecond].forEach((die, index) => {
    die.classList.toggle("selected", !els.diceSecond.hidden && index === roll.selected_index);
    die.classList.toggle("discarded", !els.diceSecond.hidden && index !== roll.selected_index);
  });
}

function cancelDiceCheck() {
  const pending = state.pendingCheck;
  if (!pending) return;
  closeDiceCheck();
  els.choicesArea.style.display = "";
  pending.focus?.focus();
}

function confirmDiceCheck() {
  const pending = state.pendingCheck;
  if (!pending || state.turnBusy || state.serviceBusy) return;
  state.pendingCheck = null;
  const choice = pending.choice;
  return submitChoice(choice.text, choice.action_id || choice.id || "", choice.check);
}

function closeDiceCheck() {
  const presentation = state.dicePresentation;
  state.dicePresentation = null;
  state.pendingCheck = null;
  stopDiceRollAnimation();
  presentation?.wake?.();
  els.diceCheckCard.style.display = "none";
  els.diceCheckBackdrop.hidden = true;
  els.gameScreen.classList.remove("dice-active");
}

function startDicePresentation(check, title) {
  showDiceCheckCard(check, title);
  const presentation = {
    startedAt: performance.now(), minimum: check ? 900 : 600,
    reducedMotion: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
    skipped: false, roll: null, wake: null,
  };
  state.dicePresentation = presentation;
  els.diceCheckActions.hidden = true;
  els.diceCheckAnimation.hidden = false;
  els.diceNatural.textContent = "?";
  els.diceNaturalSecond.textContent = "?";
  els.diceNatural.hidden = true;
  els.diceNaturalSecond.hidden = true;
  els.diceCalculation.hidden = true;
  els.diceCritical.hidden = true;
  els.diceOutcome.textContent = "判定中…";
  els.diceCheckCard.focus();
  if (!presentation.reducedMotion) {
    els.diceCheckCard.classList.add("rolling");
  } else {
    els.diceCheckCard.classList.add("instant-result");
  }
  return presentation;
}

function waitForDice(presentation, milliseconds) {
  if (state.dicePresentation !== presentation || milliseconds <= 0) return Promise.resolve();
  return new Promise(resolve => {
    const timer = window.setTimeout(() => presentation.wake?.(), milliseconds);
    presentation.wake = () => {
      window.clearTimeout(timer);
      presentation.wake = null;
      resolve();
    };
  });
}

function showDiceCalculation(roll) {
  const modifier = Number(roll.attr_mod || 0);
  els.diceCalculation.textContent = `${modifier < 0 ? "−" : "＋"}${Math.abs(modifier)} ＝ ${roll.total}`;
  els.diceCalculation.setAttribute("aria-label", `${diceFacesText(roll)} ${els.diceCalculation.textContent}`);
  els.diceCalculation.hidden = false;
}

function diceCheckSucceeded(roll) {
  if (roll.outcome) return ["success", "critical_success"].includes(roll.outcome);
  if (roll.critical_enabled !== false && roll.critical_failure) return false;
  if (roll.critical_enabled !== false && roll.critical_success) return true;
  return roll.success === true || Number(roll.total) >= Number(roll.dc);
}

function showDiceOutcome(roll) {
  const natural = roll.critical_enabled === false ? null : selectedDiceFace(roll);
  const success = diceCheckSucceeded(roll);
  els.diceOutcome.textContent = `DC ${roll.dc}　${success ? "成功" : "失敗"}`;
  els.diceOutcome.classList.toggle("success", success);
  els.diceOutcome.classList.toggle("failure", !success);
  els.diceCritical.textContent = natural === 20 ? "大成功" : natural === 1 ? "大失敗" : "";
  els.diceCritical.hidden = !els.diceCritical.textContent;
  els.diceCheckCard.classList.toggle("critical-success", natural === 20);
  els.diceCheckCard.classList.toggle("critical-failure", natural === 1);
  els.diceCheckCard.classList.toggle("crucial-failure", roll.crucial === true && !success);
}

function skipDicePresentation() {
  const presentation = state.dicePresentation;
  if (!presentation) return;
  presentation.skipped = true;
  stopDiceRollAnimation();
  els.diceCheckCard.classList.add("instant-result");
  // Until the response arrives, no final number is known on the client.
  els.diceNatural.textContent = "?";
  els.diceNaturalSecond.textContent = "?";
  if (presentation.roll) {
    showDiceFaces(presentation.roll);
    showDiceCalculation(presentation.roll);
    showDiceOutcome(presentation.roll);
  }
  presentation.wake?.();
}

async function renderTurnResponse(session, title = "判定") {
  const log = session.dice_log || [];
  const previousLog = state.session?.dice_log || [];
  const roll = log[log.length - 1];
  const isNew = log.length !== previousLog.length || diceSignature(roll) !== diceSignature(previousLog[previousLog.length - 1]);
  if (!state.session?.in_combat && (!session.in_combat || roll?.crucial === true) && isNew && isCheckRoll(roll)
      && Number(roll.dc) < 100 && roll.rolls?.length) {
    document.querySelector("#mapOverlay").style.display = "none";
    const presentation = state.dicePresentation || startDicePresentation(null, title);
    presentation.roll = roll;
    els.diceSecond.hidden = !(roll.advantage && roll.rolls.length === 2);
    showDiceAdvantage(roll);
    showDiceCrucial(roll);
    const immediate = () => presentation.skipped || presentation.reducedMotion;
    await waitForDice(presentation, immediate() ? 0 : presentation.minimum - (performance.now() - presentation.startedAt));
    if (state.dicePresentation !== presentation) return;
    els.diceOutcome.textContent = "";
    // Settle and fade within 039's existing 200ms face reveal budget.
    els.diceCheckCard.style.setProperty("--dice-settle-duration", "120ms");
    els.diceCheckCard.style.setProperty("--dice-number-duration", "80ms");
    if (immediate()) stopDiceRollAnimation();
    else settleDice();
    await waitForDice(presentation, immediate() ? 0 : 120);
    if (state.dicePresentation !== presentation) return;
    els.diceCheckCard.classList.remove("settling");
    showDiceFaces(roll);
    await waitForDice(presentation, immediate() ? 0 : 80);
    if (state.dicePresentation !== presentation) return;
    showDiceCalculation(roll);
    await waitForDice(presentation, immediate() ? 0 : 200);
    if (state.dicePresentation !== presentation) return;
    showDiceOutcome(roll);
    await waitForDice(presentation, 1200);
    if (state.dicePresentation !== presentation) return;
  }
  closeDiceCheck();
  renderSession(session);
  if (!session.in_combat && !session.game_over) {
    (state.choicesRevealed ? els.choicesList.querySelector(".choice-card") : els.dialogueBox)?.focus();
  }
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
  return [roll.created_at || "", roll.expression || "", rolls, roll.total ?? "", roll.dc ?? "", roll.success ?? ""].join("|");
}

function isCheckRoll(roll) {
  return Number(roll?.dc || 0) > 0;
}

function showDiceResult(roll) {
  if (!els.diceBanner || !els.diceRollFace || !els.diceBannerText || !roll) return;
  stopDiceRollAnimation();
  const total = Number(roll.total ?? 0);
  const dc = Number(roll.dc ?? 0);
  const hasCheck = dc > 0;
  const success = diceCheckSucceeded(roll);
  els.diceBanner.style.display = "";
  els.diceBanner.classList.toggle("success", hasCheck && success);
  els.diceBanner.classList.toggle("failure", hasCheck && !success);
  els.diceBanner.classList.toggle("neutral", !hasCheck);
  els.diceRollFace.textContent = String(total);

  const parts = [`${roll.expression || "判定"}: ${diceFacesText(roll) || total}`];
  if (typeof roll.attr_mod === "number" && roll.attr_mod !== 0) {
    const sign = roll.attr_mod > 0 ? "+" : "";
    parts.push(`${sign}${roll.attr_mod}`);
  }
  parts.push(`= ${total}`);
  if (hasCheck) {
    parts.push(` / DC${dc}`);
    if (roll.critical_enabled !== false && roll.critical_success) parts.push("大成功");
    else if (roll.critical_enabled !== false && roll.critical_failure) parts.push("大失敗");
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
    backCard.dataset.description = "";
    backCard.setAttribute("aria-describedby", "choiceDescription");
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
    const unknown = choice.visibility === "unknown";
    const hasChildren = typeof choice === "object" && Array.isArray(choice.children) && choice.children.length > 0;

    const card = document.createElement("button");
    card.type = "button";
    card.setAttribute("aria-disabled", String(!enabled));
    card.setAttribute("aria-describedby", "choiceDescription");
    card.dataset.description = enabled ? preview : disabledReason;
    card.dataset.choiceIndex = String(i);
    card.dataset.choiceText = text;
    card.dataset.actionId = typeof choice === "object" ? (choice.action_id || choice.id || "") : "";
    if (hasChildren) {
      card.dataset.choiceParent = "true";
      card.className = `choice-card choice-group ${enabled ? "" : "disabled-choice"}`;
    } else {
      card.className = `choice-card ${isCombatChoice(text, preview, risk) ? "combat-choice" : ""} ${enabled ? "" : "disabled-choice"}`;
    }
    card.classList.toggle("unknown-choice", unknown);

    const riskClass = classifyRisk(risk);

    const numberDiv = document.createElement("div");
    numberDiv.className = "choice-number";
    numberDiv.textContent = String(i + 1);

    const textDiv = document.createElement("div");
    textDiv.className = "choice-text";
    textDiv.innerHTML = rubyHtml(text);

    const bodyDiv = document.createElement("div");
    bodyDiv.className = "choice-body";
    bodyDiv.appendChild(textDiv);

    if (hasChildren && !unknown) {
      const hintSpan = document.createElement("span");
      hintSpan.className = "choice-group-hint";
      hintSpan.textContent = Array.isArray(choice.children) ? `${choice.children.length}件` : "";
      bodyDiv.appendChild(hintSpan);
    }
    if (preview && !unknown) {
      const previewDiv = document.createElement("div");
      previewDiv.className = "choice-preview";
      previewDiv.innerHTML = rubyHtml(preview);
      bodyDiv.appendChild(previewDiv);
    }
    if (risk && !hasChildren && !unknown) {
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
  highlightChoice(els.choicesList.querySelector(".choice-card"));
  els.dialogueBox.classList.remove("choices-ready");
  if (els.clickIndicator) els.clickIndicator.style.display = "none";
  choiceDebug("render-choices-visible", choiceLayoutDebug());
}

function highlightChoice(card) {
  if (!card || !els.choicesList.contains(card)) return;
  for (const row of els.choicesList.querySelectorAll(".choice-card")) {
    row.classList.toggle("highlighted", row === card);
  }
  els.choiceDescription.innerHTML = rubyHtml(card.dataset.description || "");
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
  restoreChoicePortrait(null);
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
  const npcImage = state.choicePortrait || session.dialogue_portrait_image || "";
  const locationNpcs = Array.isArray(session.location_npc_portraits)
    ? session.location_npc_portraits.filter((npc) => npc && npc.image)
    : [];
  const dialogueActive = Boolean((state.choicePortrait || session.dialogue_active) && playerImage && npcImage);
  els.spriteLayer.classList.toggle("dialogue-mode", dialogueActive);
  els.spriteLayer.classList.toggle("ensemble-mode", !dialogueActive && locationNpcs.length > 0);
  els.spriteLayer.classList.toggle("solo-mode", !dialogueActive && locationNpcs.length === 0 && Boolean(playerImage));

  els.locationPortraits.innerHTML = dialogueActive ? "" : locationNpcs.map((npc) => (
    `<figure class="location-portrait"><img src="${escapeAttr(npc.image)}" alt="" /><figcaption>${rubyHtml(npc.name || "")}</figcaption></figure>`
  )).join("");
  els.locationPortraits.dataset.count = String(locationNpcs.length);
  els.locationPortraits.style.display = !dialogueActive && locationNpcs.length ? "" : "none";

  els.playerPortrait.src = playerImage;
  els.playerPortrait.style.display = dialogueActive || (!locationNpcs.length && playerImage) ? "" : "none";
  els.npcPortrait.src = npcImage;
  els.npcPortrait.style.display = dialogueActive ? "" : "none";
}

function restoreChoicePortrait(portrait) {
  state.choicePortrait = portrait;
  if (state.session) renderScenePortraits(state.session, state.session.character || {});
}

function parentChoicePortrait(choice) {
  if (choice.portrait_image) return choice.portrait_image;
  const images = new Set();
  const visit = children => children.forEach(child => {
    if (child.portrait_image) images.add(child.portrait_image);
    if (child.children) visit(child.children);
  });
  visit(choice.children || []);
  return images.size === 1 ? [...images][0] : null;
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
  if (els.endingRetryButton) els.endingRetryButton.hidden = !gameOver || !state.session?.can_retry_area;
  if (!gameOver) {
    els.endingOverlay.style.display = "none";
    return;
  }
  els.endingTitle.textContent = gameOver.title || "敗北";
  const complete = ["ignis_defeated", "ignis_purified", "draco_defeated", "draco_defeated_with_ignis"].includes(gameOver.ending);
  els.endingOverlay.classList.toggle("complete", complete);
  const endingLabel = document.querySelector("#endingLabel");
  if (endingLabel) endingLabel.textContent = complete ? "ADVENTURE COMPLETE" : "GAME OVER";
  els.endingReason.innerHTML = rubyHtml(gameOver.reason || "物語はここで終わりました。");
  const epilogue = document.querySelector("#endingEpilogue");
  if (epilogue) {
    epilogue.replaceChildren(...(gameOver.epilogue || []).map((line, index) => {
      const item = document.createElement("li");
      item.innerHTML = rubyHtml(line);
      item.style.animationDelay = `${0.6 + index * 0.5}s`;
      return item;
    }));
  }
  els.endingOverlay.style.display = "";
}

async function retryArea() {
  if (!state.session?.can_retry_area || state.turnBusy || state.combatBusy || state.serviceBusy) return;
  state.turnBusy = true;
  els.endingRetryButton.disabled = true;
  try {
    const session = await serviceRequest("retry", {});
    clearPendingChoices();
    renderSession(session);
  } catch (error) {
    els.endingReason.textContent = error.message;
  } finally {
    state.turnBusy = false;
    els.endingRetryButton.disabled = false;
  }
}

function clearPendingChoices() {
  state.pendingChoices = [];
  state.choiceStack = [];
  restoreChoicePortrait(null);
  state.choicesRevealed = false;
  updateDialogueAdvanceState();
}

function revealPendingChoices() {
  choiceDebug("reveal-choices", {
    blocked: state.choicesRevealed || !state.pendingChoices.length,
  });
  if (state.turnBusy || state.pendingCheck || state.choicesRevealed || !state.pendingChoices.length) return;
  state.choicesRevealed = true;
  renderChoices(state.pendingChoices);
}

function handleChoiceListClick(event) {
  if (state.turnBusy || state.serviceBusy || state.pendingCheck) return;
  const card = event.target.closest(".choice-card");
  choiceDebug("choice-click", {
    targetTag: event.target?.tagName || "",
    targetClass: String(event.target?.className || ""),
    hasCard: Boolean(card),
    cardDisabled: card?.getAttribute("aria-disabled") === "true",
    cardIndex: card?.dataset.choiceIndex || "",
    cardText: card?.dataset.choiceText || "",
    cardParent: card?.dataset.choiceParent || "",
    actionId: card?.dataset.actionId || "",
    layout: choiceLayoutDebug(),
  });
  if (!card || !els.choicesList.contains(card) || card.getAttribute("aria-disabled") === "true") return;

  if (card.dataset.choiceText === "__back__") {
    if (state.choiceStack.length > 0) {
      const previous = state.choiceStack.pop();
      state.pendingChoices = previous.choices;
      restoreChoicePortrait(previous.portrait);
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
    state.choiceStack.push({ choices: state.pendingChoices, portrait: state.choicePortrait });
    restoreChoicePortrait(parentChoicePortrait(choice) || state.choicePortrait);
    state.pendingChoices = choice.children;
    state.choicesRevealed = true;
    renderChoices(state.pendingChoices);
    return;
  }

  const text = card.dataset.choiceText || (typeof choice === "string" ? choice : (choice && typeof choice === "object" ? choice.text : ""));
  if (choice.check && !state.session?.in_combat) openDiceCheck(choice, card);
  else if (text) submitChoice(text, card.dataset.actionId || "");
}

function renderCombat(session) {
  const combat = session.combat;
  const active = Boolean(session.in_combat && combat && combat.status);
  els.gameScreen.classList.toggle("combat-active", active);
  if (!active) {
    els.combatScreen.style.display = "none";
    if (els.combatIntro) els.combatIntro.style.display = "none";
    state.combatTargetId = "";
    state.combatLogId = "";
    state.combatLogExpanded = false;
    return;
  }

  els.combatScreen.style.display = "";
  if (state.combatLogId !== combat.id) {
    state.combatLogId = combat.id;
    state.combatLogExpanded = false;
  }
  renderCombatLogToggle();
  renderCombatIntro(combat);
  els.combatScreen.classList.toggle("busy", state.combatBusy);
  const enemies = Array.isArray(combat.enemies) ? combat.enemies : [];
  const alive = enemies.filter((enemy) => combat.presentation_state?.[enemy.id]
    ? !combat.presentation_state[enemy.id].defeated : Number(enemy.hp || 0) > 0);
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
  els.combatEnemies.innerHTML = enemies.map(enemy => combatEnemyMarkup(enemy, combat.presentation_state?.[enemy.id])).join("");

  const logs = Array.isArray(combat.log) ? combat.log : [];
  els.combatLog.innerHTML = logs.length
    ? logs.map(combatLogMarkup).join("")
    : '<div class="combat-log-entry"><strong>R1</strong><span>行動を選択してください。</span></div>';
  if (!state.combatLogExpanded) els.combatLog.scrollTop = els.combatLog.scrollHeight;

  const terminal = combat.status !== "active";
  els.combatScreen.classList.toggle("combat-terminal", terminal);
  els.combatScreen.classList.toggle("combat-defeat", combat.status === "defeat");
  els.combatScreen.classList.toggle("combat-victory", combat.status === "victory");
  els.combatResult.style.display = terminal ? "" : "none";
  els.combatActionTabs.style.display = terminal ? "none" : "";
  els.combatActions.style.display = terminal ? "none" : "grid";
  state.combatTutorial = terminal ? null : combat.tutorial || null;
  if (terminal) {
    renderCombatTutorial();
    const labels = { victory: "勝利", defeat: "敗北", fled: "撤退成功", purified: "浄化" };
    els.combatResultTitle.textContent = labels[combat.status] || "戦闘終了";
    els.combatResultText.innerHTML = rubyHtml(combat.result?.summary || "戦闘結果が確定しました。");
    els.combatResolveButton.disabled = state.combatBusy || !combat.pending_resolution;
  } else {
    state.combatActions = Array.isArray(combat.actions) ? combat.actions : [];
    renderCombatActions(state.combatActions);
  }
}

function renderCombatLogToggle() {
  els.combatScreen.classList.toggle("log-expanded", state.combatLogExpanded);
  els.combatLogToggle.setAttribute("aria-expanded", String(state.combatLogExpanded));
  els.combatLogToggle.textContent = state.combatLogExpanded ? "ログ ▴" : "ログ ▾";
}

function combatLogMarkup(entry) {
  return `<div class="combat-log-entry ${escapeAttr(entry.kind || "")}" data-event-sequence="${entry.sequence || 0}"><strong>R${entry.round || 1}</strong><span>${rubyHtml(entry.text || "")}</span></div>`;
}

function combatEnemyMarkup(enemy, resources) {
    const hp = Number(enemy.hp || 0);
    const maxHp = Math.max(1, Number(enemy.max_hp || hp || 1));
    const percent = Math.max(0, Math.min(100, (hp / maxHp) * 100));
    const selected = enemy.id === state.combatTargetId;
    const defeated = resources ? resources.defeated : hp <= 0;
    const enemyImage = enemy.image
      ? `<img class="combat-enemy-image" src="${escapeAttr(enemy.image)}" alt="" />`
      : "";
    return `<button type="button" class="combat-enemy ${selected ? "selected" : ""} ${defeated ? "defeated" : ""}"
      data-combat-target="${escapeAttr(enemy.id || "")}" ${defeated ? "disabled" : ""}>
      ${enemyImage}
      <span class="combatant-side">ENEMY</span>
      <h3>${rubyHtml(enemy.name || enemy.id || "敵")}</h3>
      <div class="combat-resource hp"><span>HP</span><i><b style="width:${percent}%"></b></i><strong>${hp}/${maxHp}</strong></div>
      ${enemy.description ? `<p>${rubyHtml(enemy.description)}</p>` : ""}
      ${renderAbilityTags(enemy.skills || [], true)}
    </button>`;
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
    { id: "tactics", label: "戦術", types: ["special", "defend", "flee"] },
  ].filter((group) => actions.some((action) => group.types.includes(action.type)));
  if (!groups.some((group) => group.id === state.combatActionTab)) {
    state.combatActionTab = groups[0]?.id || "attack";
  }
  els.combatActionTabs.innerHTML = groups.map((group) => `<button type="button" class="combat-tab ${group.id === state.combatActionTab ? "active" : ""}" data-combat-tab="${group.id}">${group.label}</button>`).join("");
  const current = groups.find((group) => group.id === state.combatActionTab);
  const visible = current ? actions.filter((action) => current.types.includes(action.type)) : [];
  els.combatActions.innerHTML = visible.map((action) => {
    const cost = action.cost ? `${String(action.cost_item_name || action.cost_type || "").toUpperCase()} ${action.cost}` : "";
    const description = action.enabled === false ? (action.disabled_reason || "使用できません") : (action.description || "");
    const label = [action.name || action.id || "行動", ...abilityTagTexts([action]), cost, description].filter(Boolean).join(" ");
    return `<button type="button" class="combat-action" aria-label="${escapeAttr(label)}" data-combat-action-type="${escapeAttr(action.type || "")}" data-combat-action-id="${escapeAttr(action.id || "")}" ${action.enabled === false ? "disabled" : ""}>
      <strong>${escapeHtml(action.name || action.id || "行動")}</strong>
      ${cost ? `<em>${escapeHtml(cost)}</em>` : ""}
      ${renderAbilityTags([action])}
      <span>${escapeHtml(description)}</span>
    </button>`;
  }).join("");
  visible.forEach((action, index) => {
    if (action.type === "item") prependItemIcon(els.combatActions.children[index].querySelector("strong"), action);
  });
  renderCombatTutorial();
}

// The first fight teaches attack -> heal after the slime's acid -> skill. Hints never block other actions.
function combatTutorialStep(tutorial, actions) {
  if (!tutorial) return null;
  const done = Array.isArray(tutorial.player_actions) ? tutorial.player_actions : [];
  const usable = (type, pick = () => true) => actions.find((action) => action.type === type && action.enabled !== false && pick(action));
  if (!done.length) {
    const attack = usable("attack");
    return attack ? { tab: "attack", action: attack, text: "まずは『攻撃』で武器を振ってみよう。敵を選んでから行動を押すと、その敵を狙える。" } : null;
  }
  if (done.length === 1 && tutorial.enemy_skill_used) {
    const potion = usable("item", (action) => action.id === "travel_potion") || usable("item", (action) => action.kind === "heal");
    if (potion) return { tab: "item", action: potion, text: `スライムの溶解液は防御を無視してくる！『道具』の${potion.name}でHPを回復しよう。` };
  }
  if (!done.includes("skill")) {
    const skill = usable("skill");
    return skill ? { tab: "skill", action: skill, text: "次は『技能』を使ってみよう。MPやSPを消費して、通常攻撃より強い効果を出せる。" } : null;
  }
  if (done.indexOf("skill") === done.length - 1) return { text: "チュートリアル完了！ここからは自由に戦おう。" };
  return null;
}

function renderCombatTutorial() {
  if (!els.combatTutorial) return;
  const step = state.combatBusy ? null : combatTutorialStep(state.combatTutorial, state.combatActions || []);
  els.combatTutorial.style.display = step ? "" : "none";
  if (!step) return;
  els.combatTutorial.innerHTML = `<b>TUTORIAL</b><span>${escapeHtml(step.text)}</span>`;
  if (!step.tab) return;
  const target = state.combatActionTab === step.tab
    ? [...els.combatActions.querySelectorAll("[data-combat-action-type]")].find((button) =>
      button.dataset.combatActionType === step.action.type && button.dataset.combatActionId === String(step.action.id || ""))
    : els.combatActionTabs.querySelector(`[data-combat-tab="${step.tab}"]`);
  if (target) target.classList.add("tutorial-target");
}

function renderCombatIntro(combat) {
  if (!els.combatIntro || !els.combatIntroText || !els.combatIntroContinue) return;
  const combatId = String(combat?.id || "");
  const introText = String(combat?.intro_text || "").trim();
  const visible = Boolean(combatId && introText && combat?.status === "active" && state.combatIntroSeenId !== combatId);
  els.combatIntro.dataset.combatId = combatId;
  els.combatIntroText.innerHTML = rubyHtml(introText);
  els.combatIntro.style.display = visible ? "" : "none";
  els.combatScreen.classList.toggle("intro-active", visible);
}

function abilityTagTexts(abilities, compact = false) {
  const tags = [];
  for (const ability of abilities || []) {
    if (!ability || typeof ability !== "object") continue;
    if (ability.damage) tags.push(`威力 ${ability.damage}`);
    if (ability.healing) tags.push(`回復 ${ability.healing}`);
    if (ability.accuracy !== undefined) tags.push(`命中 ${ability.accuracy}%`);
    if (ability.element) tags.push(elementLabel(ability.element));
    if (ability.all_targets) tags.push("全体");
    if (ability.hits_per_element) tags.push(`${ability.hits_per_element}回×${(ability.multi_elements || []).length || 1}属性`);
    if (ability.check?.dc) tags.push(`判定 DC${ability.check.dc}`);
    for (const followup of ability.followups || []) {
      if (followup?.damage) tags.push(`追撃 ${followup.damage}`);
      if (followup?.element) tags.push(`追撃 ${elementLabel(followup.element)}`);
    }
    if (compact && ability.name) tags.unshift(ability.name);
  }
  return tags;
}

function renderAbilityTags(abilities, compact = false) {
  const tags = abilityTagTexts(abilities, compact);
  if (!tags.length) return "";
  return `<div class="combat-effect-tags">${tags.slice(0, compact ? 4 : 6).map((tag) => `<i>${escapeHtml(tag)}</i>`).join("")}</div>`;
}

async function submitCombatAction(actionType, actionId) {
  if (!state.sessionId || state.combatBusy) return;
  state.combatBusy = true;
  els.combatScreen.classList.add("busy");
  renderCombatTutorial();
  try {
    const session = await fetchJson(`/api/sessions/${state.sessionId}/combat/actions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action_type: actionType, action_id: actionId, target_id: state.combatTargetId }),
    });
    await playCombatEvents(state.session, session);
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
  speakerNode.innerHTML = rubyHtml(speaker || (role === "user" ? "プレイヤー" : "GM"));

  const textNode = document.createElement("div");
  textNode.className = "text";
  textNode.innerHTML = rubyHtml(text || "");

  node.append(speakerNode, textNode);
  if (els.messages) {
    els.messages.append(node);
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  // Update galgame dialog box
  if (els.speakerName) els.speakerName.innerHTML = rubyHtml(speaker || (role === "user" ? "プレイヤー" : "GM"));
  if (els.messageText) els.messageText.innerHTML = rubyHtml(text || "");

  return textNode;
}

/* ═══════════════════════════════════════════════════
   GENERIC LIST RENDERER
   ═══════════════════════════════════════════════════ */

function renderList(target, items, emptyText, rich = false) {
  target.innerHTML = "";
  const values = items.length ? items : [emptyText];
  for (const item of values) {
    const li = document.createElement("li");
    if (rich) li.innerHTML = rubyHtml(item);
    else li.textContent = item;
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
  state.turnBusy = isBusy;
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

// Proper names show their English spelling with the katakana as ruby; element labels keep the kanji with the id as ruby.
// Only the first mention in each block carries the ruby; later names stay in English.
let rubyCache = { source: undefined, pattern: null, lookup: new Map() };

function rubyMatcher() {
  const ruby = state.session?.ruby;
  if (rubyCache.source === ruby) return rubyCache;
  const lookup = new Map();
  for (const [kana, english] of Object.entries(ruby?.names || {})) {
    const entry = { key: english, first: `<ruby>${escapeHtml(english)}<rt>${escapeHtml(kana)}</rt></ruby>`, rest: escapeHtml(english) };
    lookup.set(kana, entry);
    lookup.set(english, entry);
  }
  const elements = new Map(Object.entries(ruby?.elements || {}).map(([id, label]) =>
    [`${label}属性`, { key: id, first: `<ruby>${escapeHtml(label)}<rt>${escapeHtml(id)}</rt></ruby>属性`, rest: `${escapeHtml(label)}属性` }]));
  const alternation = (keys) => [...keys].sort((a, b) => b.length - a.length).map(escapeRegExp).join("|");
  const parts = [];
  if (lookup.size) parts.push(`(?<![ァ-ヶーA-Za-z])(?:${alternation(lookup.keys())})(?![ァ-ヶーA-Za-z])`);
  if (elements.size) parts.push(alternation(elements.keys()));
  elements.forEach((entry, key) => lookup.set(key, entry));
  rubyCache = { source: ruby, lookup, pattern: parts.length ? new RegExp(parts.join("|"), "g") : null };
  return rubyCache;
}

function rubyHtml(text) {
  const html = escapeHtml(String(text ?? ""));
  const { pattern, lookup } = rubyMatcher();
  if (!pattern) return html;
  const seen = new Set();
  return html.replace(pattern, (term) => {
    const entry = lookup.get(term);
    if (!entry) return term;
    if (seen.has(entry.key)) return entry.rest;
    seen.add(entry.key);
    return entry.first;
  });
}

function elementLabel(element) {
  const id = String(element || "");
  return state.session?.ruby?.elements?.[id] || id.toUpperCase();
}

function escapeRegExp(text) {
  return String(text).replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
}

/* ═══════════════════════════════════════════════════
   EVENT BINDINGS
   ═══════════════════════════════════════════════════ */

els.form.addEventListener("submit", submitTurn);
els.diceCheckRoll.addEventListener("click", confirmDiceCheck);
els.diceCheckCancel.addEventListener("click", cancelDiceCheck);
document.addEventListener("click", event => {
  if (state.dicePresentation || (state.pendingCheck && !els.diceCheckCard.contains(event.target))) {
    event.preventDefault();
    event.stopImmediatePropagation();
    skipDicePresentation();
  }
}, true);
document.addEventListener("keydown", event => {
  if (!state.pendingCheck && !state.dicePresentation) return;
  if (!["Enter", " ", "Escape", "Tab"].includes(event.key)) return;
  event.preventDefault();
  event.stopImmediatePropagation();
  if (event.repeat) return;
  if (state.dicePresentation) {
    if (event.key !== "Tab") skipDicePresentation();
  } else if (event.key === "Escape") {
    cancelDiceCheck();
  } else if (event.key === "Tab") {
    (document.activeElement === els.diceCheckRoll ? els.diceCheckCancel : els.diceCheckRoll).focus();
  } else {
    confirmDiceCheck();
  }
}, true);
els.startButton.addEventListener("click", startGame);
els.newSessionButton.addEventListener("click", newSession);
if (els.endingRestartButton) els.endingRestartButton.addEventListener("click", newSession);
if (els.endingRetryButton) els.endingRetryButton.addEventListener("click", retryArea);
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
    for (const card of els.characterCards.querySelectorAll(".char-card")) {
      const char = state.characters.find((item) => item.id === card.dataset.charId);
      if (char) card.querySelector("img").src = characterPortrait(char);
    }
    if (state.selectedCharacter) state.selectedCharacterImage = characterPortrait(state.selectedCharacter);
  });
}

// Config gear panel toggle
const configPanel = document.querySelector("#configPanel");
const configToggle = document.querySelector("#configToggle");
if (configToggle && configPanel) {
  configToggle.addEventListener("click", (e) => {
    e.stopPropagation();
    configPanel.classList.toggle("open");
    configToggle.setAttribute("aria-expanded", String(configPanel.classList.contains("open")));
  });
  document.addEventListener("click", (e) => {
    if (!configPanel.contains(e.target)) {
      configPanel.classList.remove("open");
      configToggle.setAttribute("aria-expanded", "false");
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
if (els.choicesList) {
  els.choicesList.addEventListener("click", handleChoiceListClick);
  for (const event of ["pointerover", "focusin"]) {
    els.choicesList.addEventListener(event, (e) => highlightChoice(e.target.closest(".choice-card")));
  }
  els.choicesList.addEventListener("keydown", (event) => {
    if (!["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) return;
    const cards = [...els.choicesList.querySelectorAll(".choice-card")];
    const index = cards.indexOf(document.activeElement);
    const next = event.key === "Home" ? 0 : event.key === "End" ? cards.length - 1
      : (index + (event.key === "ArrowDown" ? 1 : -1) + cards.length) % cards.length;
    event.preventDefault();
    cards[next]?.focus();
  });
}
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
if (els.combatLogToggle) {
  els.combatLogToggle.parentElement.addEventListener("click", () => {
    if (!window.matchMedia("(width < 768px)").matches) return;
    state.combatLogExpanded = !state.combatLogExpanded;
    renderCombatLogToggle();
    els.combatLog.scrollTop = state.combatLogExpanded ? 0 : els.combatLog.scrollHeight;
    if (state.combatLogExpanded) els.combatLogToggle.scrollIntoView({ block: "start" });
  });
}
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

document.querySelector("#shopCloseBtn").addEventListener("click", closeShop);
for (const [id, tab] of [["shopBuyTab", "buy"], ["shopSellTab", "sell"]]) {
  document.querySelector(`#${id}`).addEventListener("click", () => {
    state.shopTab = tab;
    state.shopItemId = "";
    state.shopQuantity = 1;
    renderShop();
  });
}
document.querySelector("#shopOverlay").addEventListener("keydown", event => {
  if (event.key === "Escape") { event.preventDefault(); closeShop(); }
  if (event.key !== "Tab") return;
  const buttons = [...event.currentTarget.querySelectorAll("button:not(:disabled)")];
  const first = buttons[0], last = buttons[buttons.length - 1];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
});

/* Boot */
init();

/* Maps use public, visibility-filtered node data only. */
function mapMarkup(map, mini = false) {
  const nodes = map.nodes.filter(node => node.visibility !== 'hidden');
  const symbols = {start:'●', battle:'⚔', event:'✦', rest:'☾', boss:'♛', branch:'✦', exit:'⌂', locked:'🔒', treasure:'◆'};
  const lines = map.edges.map(edge => {
    const a = nodes.find(n => n.id === edge.from), b = nodes.find(n => n.id === edge.to);
    return a && b ? `<line x1="${a.x}%" y1="${a.y}%" x2="${b.x}%" y2="${b.y}%" class="${edge.visited ? 'visited' : ''}" />` : '';
  }).join('');
  return `<svg class="map-lines" aria-hidden="true">${lines}</svg>` + nodes.map(node => {
    const unknown = node.visibility === 'adjacent-unknown';
    const label = unknown ? '？' : node.label;
    return `<${mini ? 'span' : 'button type="button"'} class="map-node ${node.visibility} ${node.current ? 'current' : ''} ${node.submap ? 'submap' : ''}"
      style="left:${node.x}%;top:${node.y}%" data-node-id="${escapeAttr(node.id)}" aria-label="${escapeAttr(label)}">
      <span class="map-symbol">${unknown ? '？' : node.visibility === 'locked' ? '🔒' : symbols[node.kind] || '●'}</span>
      ${mini ? '' : `<span class="map-label">${escapeHtml(label)}</span>`}</${mini ? 'span' : 'button'}>`;
  }).join('');
}

function renderMaps(selectedId) {
  const data = state.session?.map;
  const current = data?.maps.find(m => m.id === data.current_map_id);
  const mini = document.querySelector('#miniMap');
  document.querySelector('#mapToggleBtn').disabled = !current;
  mini.hidden = !current;
  if (!current) { document.querySelector('#mapOverlay').style.display = 'none'; return; }
  mini.innerHTML = mapMarkup(current, true);
  const selected = data.maps.find(m => m.id === selectedId) || current;
  const parent = data.maps.find(m => m.id === selected.parent);
  const breadcrumb = document.querySelector('#mapBreadcrumb');
  breadcrumb.innerHTML = `${parent ? `<button type="button" data-map-id="${escapeAttr(parent.id)}">${escapeHtml(parent.title)}</button> › ` : ''}<strong>${escapeHtml(selected.title)}</strong>`;
  breadcrumb.querySelector('button')?.addEventListener('click', () => renderMaps(parent.id));
  const full = document.querySelector('#fullMap');
  full.innerHTML = mapMarkup(selected);
  document.querySelector('#mapDetail').textContent = '';
  for (const button of full.querySelectorAll('[data-node-id]')) {
    const node = selected.nodes.find(n => n.id === button.dataset.nodeId);
    const describe = () => { document.querySelector('#mapDetail').textContent = [node.label || '？', node.recommended, node.description].filter(Boolean).join('　'); };
    button.addEventListener('mouseenter', describe);
    button.addEventListener('focus', describe);
    button.addEventListener('click', async () => {
      describe();
      if (state.turnBusy || state.serviceBusy || state.session.in_combat || state.session.game_over) return;
      if (selected.id !== current.id) {
        if (node.submap && data.maps.some(m => m.id === node.submap)) renderMaps(node.submap);
        return;
      }
      state.turnBusy = true;
      try { await renderTurnResponse(await serviceRequest('map/move', {node_id: node.id})); }
      catch (error) { document.querySelector('#mapDetail').textContent = error.message; }
      finally { state.turnBusy = false; }
    });
  }
}

function openMap() {
  renderMaps();
  document.querySelector('#mapOverlay').style.display = '';
  document.querySelector('#mapCloseBtn').focus();
}
document.querySelector('#mapToggleBtn').addEventListener('click', openMap);
document.querySelector('#miniMap').addEventListener('click', openMap);
document.querySelector('#mapCloseBtn').addEventListener('click', () => {
  document.querySelector('#mapOverlay').style.display = 'none';
  document.querySelector('#mapToggleBtn').focus();
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape') document.querySelector('#mapOverlay').style.display = 'none';
});
document.addEventListener('error', event => {
  const img = event.target;
  if (img.tagName !== 'IMG') return;
  img.classList.add('asset-placeholder');
  img.alt = img.alt || img.closest('figure')?.textContent || img.closest('.combat-enemy')?.querySelector('h3')?.textContent || '✦';
}, true);
document.addEventListener('load', event => {
  if (event.target.tagName === 'IMG') event.target.classList.remove('asset-placeholder');
}, true);
