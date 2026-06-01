const GROUPS = {
  scenes: { label: "场景", titleKey: "title" },
  locations: { label: "地点", titleKey: "title" },
  npcs: { label: "NPC", titleKey: "name" },
  items: { label: "道具", titleKey: "name" },
  clues: { label: "线索", titleKey: "title" },
};

const state = {
  files: [],
  filename: "",
  scenario: null,
  section: "scenes",
  selectedIndex: 0,
  dirty: false,
};

const els = {
  scenarioSelect: document.querySelector("#scenarioSelect"),
  filenameInput: document.querySelector("#filenameInput"),
  newButton: document.querySelector("#newButton"),
  duplicateButton: document.querySelector("#duplicateButton"),
  saveButton: document.querySelector("#saveButton"),
  statusText: document.querySelector("#statusText"),
  dirtyBadge: document.querySelector("#dirtyBadge"),
  sectionNav: document.querySelector(".section-nav"),
  listTitle: document.querySelector("#listTitle"),
  addRecordButton: document.querySelector("#addRecordButton"),
  recordList: document.querySelector("#recordList"),
  editorPane: document.querySelector("#editorPane"),
};

init();

async function init() {
  wireEvents();
  await loadScenarioList();
  const preferred = state.files.find((item) => item.filename === "dragon_rpg.json") || state.files[0];
  if (preferred) {
    await loadScenario(preferred.filename);
  } else {
    newScenario();
  }
}

function wireEvents() {
  els.scenarioSelect.addEventListener("change", () => loadScenario(els.scenarioSelect.value));
  els.filenameInput.addEventListener("input", () => {
    state.filename = els.filenameInput.value.trim();
    markDirty();
  });
  els.newButton.addEventListener("click", newScenario);
  els.duplicateButton.addEventListener("click", duplicateScenario);
  els.saveButton.addEventListener("click", saveScenario);
  els.sectionNav.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-section]");
    if (!button) return;
    state.section = button.dataset.section;
    state.selectedIndex = 0;
    render();
  });
  els.addRecordButton.addEventListener("click", addCurrentRecord);
  els.recordList.addEventListener("click", (event) => {
    const row = event.target.closest("[data-index]");
    if (!row) return;
    state.selectedIndex = Number(row.dataset.index);
    render();
  });
  els.editorPane.addEventListener("input", handleEditorInput);
  els.editorPane.addEventListener("change", handleEditorInput);
  els.editorPane.addEventListener("click", handleEditorClick);
}

async function loadScenarioList() {
  setStatus("loading scenarios");
  const data = await fetchJson("/api/scenarios");
  state.files = data.scenarios || [];
  els.scenarioSelect.innerHTML = state.files
    .map((item) => `<option value="${escapeHtml(item.filename)}">${escapeHtml(item.title || item.filename)}</option>`)
    .join("");
  setStatus(`${state.files.length} files`);
}

async function loadScenario(filename) {
  if (!filename) return;
  setStatus("loading");
  const data = await fetchJson(`/api/scenarios/${encodeURIComponent(filename)}`);
  state.filename = data.filename;
  state.scenario = ensureShape(data.scenario);
  state.selectedIndex = 0;
  state.dirty = false;
  els.filenameInput.value = state.filename;
  els.scenarioSelect.value = state.filename;
  render();
  setStatus("loaded");
}

function newScenario() {
  state.filename = "new_scenario.json";
  state.scenario = ensureShape({
    meta: { title: "新剧本", summary: "", language: "ja", initial_scene: "start" },
    rules: [],
    scenes: [{ id: "start", title: "开始", description: "", keywords: [], goals: [], fallback_choices: [] }],
    locations: [],
    npcs: [],
    items: [],
    clues: [],
    fallback_choices: [],
  });
  state.section = "meta";
  state.selectedIndex = 0;
  els.filenameInput.value = state.filename;
  markDirty();
  render();
}

function duplicateScenario() {
  if (!state.scenario) return;
  const base = state.filename.replace(/\.json$/i, "") || "scenario";
  state.filename = `${base}_copy.json`;
  els.filenameInput.value = state.filename;
  markDirty();
  render();
}

async function saveScenario() {
  if (!state.scenario) return;
  const filename = state.filename.trim();
  if (!filename.endsWith(".json")) {
    setStatus("filename must end with .json", true);
    return;
  }
  const exists = state.files.some((item) => item.filename === filename);
  const url = exists ? `/api/scenarios/${encodeURIComponent(filename)}` : "/api/scenarios";
  const method = exists ? "PUT" : "POST";
  const body = exists ? { scenario: state.scenario } : { filename, scenario: state.scenario };
  setStatus("saving");
  const data = await fetchJson(url, { method, body: JSON.stringify(body) });
  state.filename = data.filename;
  state.scenario = ensureShape(data.scenario);
  state.dirty = false;
  await loadScenarioList();
  els.filenameInput.value = state.filename;
  els.scenarioSelect.value = state.filename;
  render();
  setStatus("saved");
}

function render() {
  if (!state.scenario) return;
  document.querySelectorAll(".section-nav button").forEach((button) => {
    button.classList.toggle("active", button.dataset.section === state.section);
  });
  els.dirtyBadge.textContent = state.dirty ? "unsaved" : "saved";
  els.dirtyBadge.classList.toggle("dirty", state.dirty);
  renderList();
  renderEditor();
}

function renderList() {
  const section = state.section;
  if (section === "hybrid") {
    els.addRecordButton.style.display = "none";
    els.listTitle.textContent = "Hybrid prepared turns";
    const scenes = state.scenario.scenes || [];
    els.recordList.innerHTML = scenes
      .map((scene, index) => {
        const count = scene.hybrid?.prepared_turns?.length || 0;
        const title = scene.title || scene.id || `Scene ${index + 1}`;
        return `<button class="record-row ${index === state.selectedIndex ? "active" : ""}" data-index="${index}" type="button">
          <strong>${escapeHtml(title)}</strong><span>${escapeHtml(scene.id || "")} · ${count} turns</span>
        </button>`;
      })
      .join("");
    return;
  }
  const group = GROUPS[section];
  els.addRecordButton.style.display = group ? "" : "none";
  els.listTitle.textContent = group ? group.label : sectionLabel(section);
  if (!group) {
    els.recordList.innerHTML = `<p class="summary-line">${escapeHtml(summaryForSection(section))}</p>`;
    return;
  }
  const records = state.scenario[section] || [];
  els.recordList.innerHTML = records
    .map((record, index) => {
      const title = record[group.titleKey] || record.title || record.name || record.id || `${group.label} ${index + 1}`;
      const sub = record.id || record.description || "";
      return `<button class="record-row ${index === state.selectedIndex ? "active" : ""}" data-index="${index}" type="button">
        <strong>${escapeHtml(title)}</strong><span>${escapeHtml(sub)}</span>
      </button>`;
    })
    .join("");
}

function renderEditor() {
  if (state.section === "meta") return renderMeta();
  if (state.section === "rules") return renderStringList("rules", "规则");
  if (state.section === "fallback") return renderChoices("fallback_choices", state.scenario.fallback_choices || [], "全局 fallback choices");
  if (state.section === "hybrid") return renderHybridEditor();
  if (state.section === "json") return renderJsonEditor();
  return renderRecordEditor(state.section);
}

function renderMeta() {
  const meta = state.scenario.meta;
  const sceneOptions = state.scenario.scenes
    .map((scene) => `<option value="${escapeHtml(scene.id)}" ${scene.id === meta.initial_scene ? "selected" : ""}>${escapeHtml(scene.title || scene.id)}</option>`)
    .join("");
  els.editorPane.innerHTML = `<div class="editor-form">
    <div class="form-grid">
      ${field("标题", "meta.title", meta.title || "")}
      ${field("语言", "meta.language", meta.language || "ja")}
      <label class="wide">摘要<textarea data-path="meta.summary">${escapeHtml(meta.summary || "")}</textarea></label>
      <label>默认起始场景<select data-path="meta.initial_scene">${sceneOptions}</select></label>
    </div>
  </div>`;
}

function renderStringList(key, title) {
  const values = state.scenario[key] || [];
  els.editorPane.innerHTML = `<div class="editor-form">
    <h2>${escapeHtml(title)}</h2>
    <div class="line-list">
      ${values.map((value, index) => `<div class="line-row">
        <input data-list="${key}" data-index="${index}" value="${escapeAttr(value)}" />
        <button class="danger" data-remove-list="${key}" data-index="${index}" type="button">删除</button>
      </div>`).join("")}
    </div>
    <button data-add-list="${key}" type="button">添加${escapeHtml(title)}</button>
  </div>`;
}

function renderRecordEditor(section) {
  const records = state.scenario[section] || [];
  const record = records[state.selectedIndex];
  const group = GROUPS[section];
  if (!record) {
    els.editorPane.innerHTML = `<div class="editor-form"><p class="summary-line">还没有${escapeHtml(group.label)}。</p></div>`;
    return;
  }
  const titleKey = group.titleKey;
  const common = `<div class="form-grid">
    ${field("ID", `${section}.${state.selectedIndex}.id`, record.id || "")}
    ${field(titleKey === "name" ? "名称" : "标题", `${section}.${state.selectedIndex}.${titleKey}`, record[titleKey] || "")}
    <label class="wide">描述<textarea data-path="${section}.${state.selectedIndex}.description">${escapeHtml(record.description || "")}</textarea></label>
    ${field("关键词，用逗号分隔", `${section}.${state.selectedIndex}.keywords`, toCsv(record.keywords || []), true)}
  </div>`;
  const sceneFields = section === "scenes" ? `<h3 class="section-title">场景节点</h3>
    <div class="form-grid">
      ${field("目标，用逗号分隔", `${section}.${state.selectedIndex}.goals`, toCsv(record.goals || []), true)}
      ${field("可命中地点 IDs", `${section}.${state.selectedIndex}.location_ids`, toCsv(record.location_ids || []), true)}
      ${field("可命中 NPC IDs", `${section}.${state.selectedIndex}.npc_ids`, toCsv(record.npc_ids || []), true)}
      ${field("可命中道具 IDs", `${section}.${state.selectedIndex}.item_ids`, toCsv(record.item_ids || []), true)}
      ${field("可命中线索 IDs", `${section}.${state.selectedIndex}.clue_ids`, toCsv(record.clue_ids || []), true)}
      ${field("后续场景 IDs", `${section}.${state.selectedIndex}.next_scene_ids`, toCsv(record.next_scene_ids || []), true)}
    </div>
    <h3 class="section-title">节点 fallback choices</h3>
    ${choicesMarkup(`${section}.${state.selectedIndex}.fallback_choices`, record.fallback_choices || [])}` : "";
  const itemFields = section === "items" ? `<h3 class="section-title">道具效果</h3>
    <label>效果<textarea data-path="${section}.${state.selectedIndex}.effect">${escapeHtml(record.effect || "")}</textarea></label>` : "";
  els.editorPane.innerHTML = `<div class="editor-form">
    ${common}
    ${itemFields}
    ${sceneFields}
    <button class="danger" data-remove-record="${section}" data-index="${state.selectedIndex}" type="button">删除${escapeHtml(group.label)}</button>
  </div>`;
}

function renderChoices(path, choices, title) {
  els.editorPane.innerHTML = `<div class="editor-form">
    <h2>${escapeHtml(title)}</h2>
    ${choicesMarkup(path, choices)}
  </div>`;
}

function renderHybridEditor() {
  const scene = state.scenario.scenes[state.selectedIndex];
  if (!scene) {
    els.editorPane.innerHTML = `<div class="editor-form"><p class="summary-line">No scene selected.</p></div>`;
    return;
  }
  ensureHybridShape(scene);
  const basePath = `scenes.${state.selectedIndex}.hybrid`;
  const turns = scene.hybrid.prepared_turns || [];
  els.editorPane.innerHTML = `<div class="editor-form">
    <h2>Hybrid prepared turns · ${escapeHtml(scene.title || scene.id || "")}</h2>
    <div class="form-grid">
      ${field("Mode", `${basePath}.mode`, scene.hybrid.mode || "prepared_gm_turns")}
      <label class="wide">Summary<textarea data-path="${basePath}.summary">${escapeHtml(scene.hybrid.summary || "")}</textarea></label>
    </div>
    <h3 class="section-title">Prepared GM turns</h3>
    <div class="prepared-turn-list">
      ${turns.map((turn, index) => preparedTurnMarkup(basePath, turn, index)).join("")}
    </div>
    <button data-add-prepared-turn="${basePath}.prepared_turns" type="button">Add prepared turn</button>
  </div>`;
}

function preparedTurnMarkup(basePath, turn, index) {
  const path = `${basePath}.prepared_turns.${index}`;
  const draft = turn.draft || {};
  return `<section class="prepared-turn">
    <div class="prepared-turn-head">
      <h4>${escapeHtml(turn.id || `turn_${index + 1}`)}</h4>
      <button class="danger" data-remove-prepared-turn="${basePath}.prepared_turns" data-index="${index}" type="button">Remove</button>
    </div>
    <div class="form-grid">
      ${field("ID", `${path}.id`, turn.id || "")}
      ${field("Purpose", `${path}.purpose`, turn.purpose || "choice_response")}
      ${field("Source choice", `${path}.source_choice`, turn.source_choice || "")}
      ${field("Player intent", `${path}.player_intent`, turn.player_intent || "")}
      ${field("Trigger keywords", `${path}.trigger_keywords`, toCsv(turn.trigger_keywords || []), true)}
      <label class="wide">GM text<textarea data-path="${path}.draft.gm_text">${escapeHtml(draft.gm_text || "")}</textarea></label>
      <label class="wide">System log<textarea data-path="${path}.draft.system_log">${escapeHtml(draft.system_log || "")}</textarea></label>
      ${field("Dice type", `${path}.draft.dice_type`, draft.dice_type || "1d20")}
      ${field("Dice DC", `${path}.draft.dice_dc`, draft.dice_dc ?? 10, false, true)}
      <label class="wide">State delta JSON<textarea data-json-path="${path}.draft.state_delta" spellcheck="false">${escapeHtml(JSON.stringify(draft.state_delta || {}, null, 2))}</textarea></label>
      ${field("Rewrite notes", `${path}.rewrite_notes`, toCsv(turn.rewrite_notes || []), true)}
    </div>
    <h4 class="mini-title">Choices</h4>
    ${choicesMarkup(`${path}.draft.choices`, draft.choices || [])}
  </section>`;
}

function renderJsonEditor() {
  els.editorPane.innerHTML = `<div class="editor-form">
    <textarea id="rawJsonInput" class="raw-json" spellcheck="false">${escapeHtml(JSON.stringify(state.scenario, null, 2))}</textarea>
    <button id="applyJsonButton" type="button">应用 JSON</button>
  </div>`;
}

function handleEditorInput(event) {
  const target = event.target;
  if (target.dataset.jsonPath) {
    markDirty();
    if (event.type !== "change") return;
    try {
      setByPath(state.scenario, target.dataset.jsonPath, JSON.parse(target.value || "{}"));
      setStatus("json applied");
    } catch (error) {
      setStatus(`Invalid JSON: ${error.message}`, true);
    }
    return;
  }
  if (target.dataset.path) {
    let value = target.dataset.csv === "true" ? fromCsv(target.value) : target.value;
    if (target.dataset.number === "true") {
      const parsed = Number(target.value);
      value = Number.isFinite(parsed) ? parsed : target.value;
    }
    setByPath(state.scenario, target.dataset.path, value);
    if (target.dataset.path.endsWith(".id")) syncInitialSceneAfterIdEdit();
    markDirty();
    if (target.dataset.path.includes(".id") || target.dataset.path.includes(".title") || target.dataset.path.includes(".name")) renderList();
  }
  if (target.dataset.list) {
    state.scenario[target.dataset.list][Number(target.dataset.index)] = target.value;
    markDirty();
  }
  if (target.dataset.choicePath) {
    const choices = getByPath(state.scenario, target.dataset.choicePath, []);
    const choice = choices[Number(target.dataset.index)];
    choice[target.dataset.choiceField] = target.value;
    markDirty();
  }
}

function handleEditorClick(event) {
  const target = event.target.closest("button");
  if (!target) return;
  if (target.dataset.addList) {
    state.scenario[target.dataset.addList].push("");
    markDirty();
    renderEditor();
  }
  if (target.dataset.removeList) {
    state.scenario[target.dataset.removeList].splice(Number(target.dataset.index), 1);
    markDirty();
    renderEditor();
  }
  if (target.dataset.addChoice) {
    const choices = getByPath(state.scenario, target.dataset.addChoice, []);
    setByPath(state.scenario, target.dataset.addChoice, choices);
    choices.push({ text: "", preview: "", risk: "" });
    markDirty();
    renderEditor();
  }
  if (target.dataset.removeChoice) {
    const choices = getByPath(state.scenario, target.dataset.removeChoice, []);
    choices.splice(Number(target.dataset.index), 1);
    markDirty();
    renderEditor();
  }
  if (target.dataset.addPreparedTurn) {
    const turns = getByPath(state.scenario, target.dataset.addPreparedTurn, []);
    setByPath(state.scenario, target.dataset.addPreparedTurn, turns);
    turns.push(newPreparedTurn(turns.length + 1));
    markDirty();
    render();
  }
  if (target.dataset.removePreparedTurn) {
    const turns = getByPath(state.scenario, target.dataset.removePreparedTurn, []);
    turns.splice(Number(target.dataset.index), 1);
    markDirty();
    render();
  }
  if (target.dataset.removeRecord) {
    const group = target.dataset.removeRecord;
    state.scenario[group].splice(Number(target.dataset.index), 1);
    state.selectedIndex = Math.max(0, state.selectedIndex - 1);
    markDirty();
    render();
  }
  if (target.id === "applyJsonButton") {
    try {
      state.scenario = ensureShape(JSON.parse(document.querySelector("#rawJsonInput").value));
      markDirty();
      render();
      setStatus("json applied");
    } catch (error) {
      setStatus(error.message, true);
    }
  }
}

function addCurrentRecord() {
  const section = state.section;
  const group = GROUPS[section];
  if (!group) return;
  const next = state.scenario[section].length + 1;
  const record = { id: `${section.slice(0, -1)}_${next}`, description: "", keywords: [] };
  record[group.titleKey] = `${group.label} ${next}`;
  if (section === "scenes") {
    Object.assign(record, { goals: [], location_ids: [], npc_ids: [], item_ids: [], clue_ids: [], fallback_choices: [] });
  }
  state.scenario[section].push(record);
  state.selectedIndex = state.scenario[section].length - 1;
  markDirty();
  render();
}

function ensureShape(scenario) {
  scenario.meta = scenario.meta && typeof scenario.meta === "object" ? scenario.meta : {};
  scenario.meta.title ||= "Untitled";
  scenario.meta.summary ||= "";
  scenario.meta.language ||= "ja";
  scenario.rules = Array.isArray(scenario.rules) ? scenario.rules : [];
  Object.keys(GROUPS).forEach((key) => {
    scenario[key] = Array.isArray(scenario[key]) ? scenario[key] : [];
  });
  if (!scenario.scenes.length) {
    scenario.scenes.push({ id: "start", title: "开始", description: "", keywords: [], goals: [], fallback_choices: [] });
  }
  scenario.meta.initial_scene ||= scenario.scenes[0].id || "start";
  scenario.fallback_choices = normalizeChoices(scenario.fallback_choices);
  scenario.scenes.forEach((scene) => {
    scene.fallback_choices = normalizeChoices(scene.fallback_choices);
    if (scene.hybrid) ensureHybridShape(scene);
  });
  return scenario;
}

function ensureHybridShape(scene) {
  scene.hybrid = scene.hybrid && typeof scene.hybrid === "object" ? scene.hybrid : {};
  scene.hybrid.mode ||= "prepared_gm_turns";
  scene.hybrid.summary ||= "";
  scene.hybrid.prepared_turns = Array.isArray(scene.hybrid.prepared_turns) ? scene.hybrid.prepared_turns : [];
  scene.hybrid.prepared_turns.forEach((turn, index) => {
    turn.id ||= `prepared_turn_${index + 1}`;
    turn.purpose ||= index === 0 ? "opening" : "choice_response";
    turn.source_choice ||= "";
    turn.player_intent ||= "";
    turn.trigger_keywords = Array.isArray(turn.trigger_keywords) ? turn.trigger_keywords : [];
    turn.rewrite_notes = Array.isArray(turn.rewrite_notes) ? turn.rewrite_notes : [];
    turn.draft = turn.draft && typeof turn.draft === "object" ? turn.draft : {};
    turn.draft.gm_text ||= "";
    turn.draft.system_log ||= "";
    turn.draft.dice_type ||= "1d20";
    turn.draft.dice_dc = Number.isFinite(Number(turn.draft.dice_dc)) ? Number(turn.draft.dice_dc) : 10;
    turn.draft.state_delta = turn.draft.state_delta && typeof turn.draft.state_delta === "object" ? turn.draft.state_delta : {};
    turn.draft.choices = normalizeChoices(turn.draft.choices);
  });
  return scene.hybrid;
}

function newPreparedTurn(index) {
  return {
    id: `prepared_turn_${index}`,
    purpose: index === 1 ? "opening" : "choice_response",
    source_choice: "",
    player_intent: "",
    trigger_keywords: [],
    draft: {
      gm_text: "",
      system_log: "",
      dice_type: "1d20",
      dice_dc: 10,
      state_delta: {},
      choices: [],
    },
    rewrite_notes: [],
  };
}

function normalizeChoices(value) {
  if (!Array.isArray(value)) return [];
  return value
    .map((choice) => {
      if (typeof choice === "string") return { text: choice, preview: "", risk: "" };
      return {
        text: choice?.text || "",
        preview: choice?.preview || "",
        risk: choice?.risk || "",
      };
    });
}

function syncInitialSceneAfterIdEdit() {
  const ids = state.scenario.scenes.map((scene) => scene.id);
  if (!ids.includes(state.scenario.meta.initial_scene)) {
    state.scenario.meta.initial_scene = ids[0] || "start";
  }
}

function choicesMarkup(path, choices) {
  return `<div class="line-list">
    ${choices.map((choice, index) => `<div class="choice-row">
      <input data-choice-path="${path}" data-choice-field="text" data-index="${index}" value="${escapeAttr(choice.text || "")}" placeholder="text" />
      <input data-choice-path="${path}" data-choice-field="preview" data-index="${index}" value="${escapeAttr(choice.preview || "")}" placeholder="preview" />
      <input data-choice-path="${path}" data-choice-field="risk" data-index="${index}" value="${escapeAttr(choice.risk || "")}" placeholder="risk" />
      <button class="danger" data-remove-choice="${path}" data-index="${index}" type="button">删除</button>
    </div>`).join("")}
    <button data-add-choice="${path}" type="button">添加选项</button>
  </div>`;
}

function field(label, path, value, csv = false, number = false) {
  return `<label>${escapeHtml(label)}<input data-path="${path}" data-csv="${csv ? "true" : "false"}" data-number="${number ? "true" : "false"}" value="${escapeAttr(value)}" /></label>`;
}

function sectionLabel(section) {
  return ({ meta: "基本信息", rules: "规则", hybrid: "Hybrid", fallback: "全局选项", json: "JSON" })[section] || section;
}

function summaryForSection(section) {
  if (section === "meta") return "编辑标题、摘要、语言和起始场景。";
  if (section === "rules") return `${state.scenario.rules.length} 条规则`;
  if (section === "hybrid") return `${state.scenario.scenes.length} scenes with editable prepared turns`;
  if (section === "fallback") return `${state.scenario.fallback_choices.length} 个全局选项`;
  if (section === "json") return "直接编辑完整 JSON。";
  return "";
}

function markDirty() {
  state.dirty = true;
  els.dirtyBadge.textContent = "unsaved";
  els.dirtyBadge.classList.add("dirty");
}

function setStatus(text, isError = false) {
  els.statusText.textContent = text;
  els.statusText.style.color = isError ? "var(--danger)" : "var(--muted)";
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : {};
  if (!response.ok) {
    throw new Error(data.detail || response.statusText);
  }
  return data;
}

function getByPath(object, path, fallback) {
  const parts = path.split(".");
  let current = object;
  for (const part of parts) {
    if (current == null) return fallback;
    current = current[part];
  }
  return current == null ? fallback : current;
}

function setByPath(object, path, value) {
  const parts = path.split(".");
  let current = object;
  for (const part of parts.slice(0, -1)) {
    if (current[part] == null) current[part] = /^\d+$/.test(part) ? [] : {};
    current = current[part];
  }
  current[parts[parts.length - 1]] = value;
}

function toCsv(value) {
  return Array.isArray(value) ? value.join(", ") : "";
}

function fromCsv(value) {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function escapeAttr(value) {
  return escapeHtml(value).replaceAll('"', "&quot;");
}
