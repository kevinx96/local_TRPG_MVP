const state = {
  sessionId: null,
  currentAssistant: null,
};

const els = {
  newSessionButton: document.querySelector("#newSessionButton"),
  sceneTitle: document.querySelector("#sceneTitle"),
  backendInfo: document.querySelector("#backendInfo"),
  messages: document.querySelector("#messages"),
  form: document.querySelector("#turnForm"),
  input: document.querySelector("#playerInput"),
  sendButton: document.querySelector("#sendButton"),
  diceSelect: document.querySelector("#diceSelect"),
  characterName: document.querySelector("#characterName"),
  characterDescription: document.querySelector("#characterDescription"),
  inventory: document.querySelector("#inventory"),
  diceLog: document.querySelector("#diceLog"),
  systemLogs: document.querySelector("#systemLogs"),
  hpBar: document.querySelector("#hpBar"),
  mpBar: document.querySelector("#mpBar"),
  spBar: document.querySelector("#spBar"),
  hpText: document.querySelector("#hpText"),
  mpText: document.querySelector("#mpText"),
  spText: document.querySelector("#spText"),
};

async function init() {
  await loadConfig();
  await createSession();
}

async function loadConfig() {
  try {
    const config = await fetchJson("/api/config");
    els.backendInfo.textContent = `${config.active_backend} / ${config.model}`;
  } catch {
    els.backendInfo.textContent = "設定を取得できません";
  }
}

async function createSession() {
  setBusy(true);
  try {
    const session = await fetchJson("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ scenario_path: "host/prompt/text/dragon_rpg.txt" }),
    });
    state.sessionId = session.id;
    renderSession(session);
  } finally {
    setBusy(false);
  }
}

async function submitTurn(event) {
  event.preventDefault();
  const text = els.input.value.trim();
  if (!text || !state.sessionId) return;
  els.input.value = "";
  addMessage("user", "プレイヤー", text);
  state.currentAssistant = addMessage("assistant", "GM", "");
  setBusy(true);
  try {
    const response = await fetch(`/api/sessions/${state.sessionId}/turn`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text, dice: els.diceSelect.value }),
    });
    if (!response.ok || !response.body) {
      throw new Error(await response.text());
    }
    await readNdjsonStream(response.body);
  } catch (error) {
    appendAssistantText(`\nエラー: ${error.message}`);
  } finally {
    state.currentAssistant = null;
    setBusy(false);
  }
}

async function readNdjsonStream(body) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";
    for (const line of lines) {
      if (!line.trim()) continue;
      handleEvent(JSON.parse(line));
    }
  }
  if (buffer.trim()) handleEvent(JSON.parse(buffer));
}

function handleEvent(event) {
  if (event.type === "token") {
    appendAssistantText(event.payload);
  }
  if (event.type === "state") {
    renderSession(event.payload);
  }
  if (event.type === "error") {
    appendAssistantText(`\n${event.payload}`);
  }
}

function renderSession(session) {
  state.sessionId = session.id;
  const character = session.character;
  els.sceneTitle.textContent = session.current_scene || session.scenario_title || "開始";
  els.characterName.textContent = character.name || "冒険者";
  els.characterDescription.textContent = character.description || "";
  renderMeter("hp", character);
  renderMeter("mp", character);
  renderMeter("sp", character);
  renderList(els.inventory, character.inventory || [], "所持品なし");
  renderList(
    els.diceLog,
    (session.dice_log || []).slice(-5).reverse().map((roll) => `${roll.expression}: ${roll.rolls.join(", ")} = ${roll.total}`),
    "判定なし",
  );
  renderList(
    els.systemLogs,
    (session.system_logs || []).slice(-8).reverse().map((entry) => entry.text),
    "ログなし",
  );
  renderMessages(session.messages || []);
}

function renderMeter(stat, character) {
  const value = Number(character[stat] || 0);
  const max = Number(character[`max_${stat}`] || value || 1);
  const percent = Math.max(0, Math.min(100, (value / max) * 100));
  els[`${stat}Bar`].style.width = `${percent}%`;
  els[`${stat}Text`].textContent = `${value}/${max}`;
}

function renderList(target, items, emptyText) {
  target.innerHTML = "";
  const values = items.length ? items : [emptyText];
  for (const item of values) {
    const li = document.createElement("li");
    li.textContent = item;
    target.append(li);
  }
}

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

function appendAssistantText(text) {
  if (!state.currentAssistant) {
    state.currentAssistant = addMessage("assistant", "GM", "");
  }
  state.currentAssistant.textContent += text;
  els.messages.scrollTop = els.messages.scrollHeight;
}

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function setBusy(isBusy) {
  els.sendButton.disabled = isBusy;
  els.newSessionButton.disabled = isBusy;
}

els.form.addEventListener("submit", submitTurn);
els.newSessionButton.addEventListener("click", createSession);
init();
