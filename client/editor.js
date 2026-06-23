const GROUPS = {
  scenes: { label: "场景", titleKey: "title" },
  locations: { label: "地点", titleKey: "title" },
  npcs: { label: "NPC", titleKey: "name" },
  items: { label: "道具", titleKey: "name" },
  clues: { label: "线索", titleKey: "title" },
  enemies: { label: "敌人", titleKey: "name" },
  attribute_defs: { label: "属性定义", titleKey: "name" },
  characters: { label: "角色", titleKey: "name" },
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
    attribute_defs: [],
    characters: [],
    enemies: [],
    combat_choices: [],
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
    const locations = state.scenario.locations || [];
    els.recordList.innerHTML = locations
      .map((loc, index) => {
        const count = loc.hybrid?.prepared_turns?.length || 0;
        const title = loc.title || loc.id || `Location ${index + 1}`;
        return `<button class="record-row ${index === state.selectedIndex ? "active" : ""}" data-index="${index}" type="button">
          <strong>${escapeHtml(title)}</strong><span>${escapeHtml(loc.id || "")} · ${count} turns</span>
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
  if (state.section === "combat") return renderChoices("combat_choices", state.scenario.combat_choices || [], "全局战斗选项");
  if (state.section === "hybrid") return renderHybridEditor();
  if (state.section === "json") return renderJsonEditor();
  if (state.section === "attribute_defs") return renderAttributeDefsEditor();
  if (state.section === "characters") return renderCharactersEditor();
  if (state.section === "enemies") return renderEnemiesEditor();
  return renderRecordEditor(state.section);
}

function renderMeta() {
  const meta = state.scenario.meta;
  const sceneOptions = state.scenario.scenes
    .map((scene) => `<option value="${escapeHtml(scene.id)}" ${scene.id === meta.initial_scene ? "selected" : ""}>${escapeHtml(scene.title || scene.id)}</option>`)
    .join("");
  const actionFields = (section === "scenes" || section === "locations")
    ? actionsJsonMarkup(`${section}.${state.selectedIndex}.actions`, record.actions || [])
    : "";
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
  const sceneFields = section === "scenes" ? `<h3 class="section-title">场景设定</h3>
    <div class="form-grid">
      ${field("目标，用逗号分隔", `${section}.${state.selectedIndex}.goals`, toCsv(record.goals || []), true)}
      ${field("绑定地点 IDs", `${section}.${state.selectedIndex}.location_ids`, toCsv(record.location_ids || []), true)}
      ${field("后续场景 IDs", `${section}.${state.selectedIndex}.next_scene_ids`, toCsv(record.next_scene_ids || []), true)}
    </div>` : "";
  const itemFields = section === "items" ? `<h3 class="section-title">道具效果</h3>
    <label>效果<textarea data-path="${section}.${state.selectedIndex}.effect">${escapeHtml(record.effect || "")}</textarea></label>` : "";
  const locationFields = section === "locations" ? `<h3 class="section-title">关联实体</h3>
    <div class="relation-grid">
      ${relationPicker("NPC", `${section}.${state.selectedIndex}.npc_ids`, record.npc_ids || [], state.scenario.npcs || [])}
      ${relationPicker("道具", `${section}.${state.selectedIndex}.item_ids`, record.item_ids || [], state.scenario.items || [])}
      ${relationPicker("线索", `${section}.${state.selectedIndex}.clue_ids`, record.clue_ids || [], state.scenario.clues || [])}
      ${relationPicker("敌人", `${section}.${state.selectedIndex}.enemy_ids`, record.enemy_ids || [], state.scenario.enemies || [])}
    </div>
    <h3 class="section-title">可达地点 IDs</h3>
    ${field("用逗号分隔", `locations.${state.selectedIndex}.connected_location_ids`, toCsv(record.connected_location_ids || []), true)}
    <h3 class="section-title">地点选项</h3>
    ${choicesMarkup(`locations.${state.selectedIndex}.choices`, record.choices || [])}` : "";
  els.editorPane.innerHTML = `<div class="editor-form">
    ${common}
    ${itemFields}
    ${locationFields}
    ${sceneFields}
    ${actionFields}
    <button class="danger" data-remove-record="${section}" data-index="${state.selectedIndex}" type="button">删除${escapeHtml(group.label)}</button>
  </div>`;
}

function renderAttributeDefsEditor() {
  const records = state.scenario.attribute_defs || [];
  const record = records[state.selectedIndex];
  if (!record) {
    els.editorPane.innerHTML = `<div class="editor-form"><p class="summary-line">还没有属性定义。</p></div>`;
    return;
  }
  els.editorPane.innerHTML = `<div class="editor-form">
    <div class="form-grid">
      ${field("ID", `attribute_defs.${state.selectedIndex}.id`, record.id || "")}
      ${field("名称", `attribute_defs.${state.selectedIndex}.name`, record.name || "")}
      ${field("初始数值", `attribute_defs.${state.selectedIndex}.initial_value`, record.initial_value ?? 8, false, true)}
    </div>
    <button class="danger" data-remove-record="attribute_defs" data-index="${state.selectedIndex}" type="button">删除属性定义</button>
  </div>`;
}

function renderCharactersEditor() {
  const records = state.scenario.characters || [];
  const record = records[state.selectedIndex];
  if (!record) {
    els.editorPane.innerHTML = `<div class="editor-form"><p class="summary-line">还没有角色。</p></div>`;
    return;
  }
  const basePath = `characters.${state.selectedIndex}`;
  const attrDefs = state.scenario.attribute_defs || [];
  const attrs = record.attributes || {};
  const attrInputs = attrDefs.map((def, ai) => {
    const attrId = def.id || "";
    const attrName = def.name || attrId || "";
    const value = attrs[attrId] ?? def.initial_value ?? 8;
    return field(attrName, `${basePath}.attributes.${escapeHtml(attrId)}`, value, false, true);
  }).join("");

  const inventory = record.inventory || [];
  const inventoryRows = inventory.map((item, ii) => `<div class="item-row">
    <input data-inv-path="${basePath}.inventory" data-inv-field="name" data-index="${ii}" value="${escapeAttr(item.name || "")}" placeholder="名称" />
    <input data-inv-path="${basePath}.inventory" data-inv-field="description" data-index="${ii}" value="${escapeAttr(item.description || "")}" placeholder="描述" />
    <input data-inv-path="${basePath}.inventory" data-inv-field="effect" data-index="${ii}" value="${escapeAttr(item.effect || "")}" placeholder="效果" />
    <input data-inv-path="${basePath}.inventory" data-inv-field="quantity" data-index="${ii}" value="${escapeAttr(item.quantity ?? 1)}" placeholder="数量" style="width:60px" />
    <button class="danger" data-remove-inv="${basePath}.inventory" data-index="${ii}" type="button">删除</button>
  </div>`).join("");

  const equip = Array.isArray(record.equipment) ? record.equipment : [];
  const equipRows = equip.map((eq, ei) => `<div class="line-row">
    <input data-eq-path="${basePath}.equipment" data-index="${ei}" value="${escapeAttr(eq)}" />
    <button class="danger" data-remove-eq="${basePath}.equipment" data-index="${ei}" type="button">删除</button>
  </div>`).join("");

  els.editorPane.innerHTML = `<div class="editor-form">
    <h2>${escapeHtml(record.name || record.id || "新角色")}</h2>
    <div class="form-grid">
      ${field("ID", `${basePath}.id`, record.id || "")}
      ${field("角色名", `${basePath}.name`, record.name || "")}
      ${field("预设名称", `${basePath}.default_name`, record.default_name || "")}
      <label class="wide">描述<textarea data-path="${basePath}.description">${escapeHtml(record.description || "")}</textarea></label>
      ${field("头像路径", `${basePath}.image`, record.image || "")}
      ${field("女性头像路径", `${basePath}.image_female`, record.image_female || "")}
    </div>
    <h3 class="section-title">基本属性</h3>
    <div class="form-grid">
      ${field("HP", `${basePath}.hp`, record.hp ?? 20, false, true)}
      ${field("Max HP", `${basePath}.max_hp`, record.max_hp ?? 20, false, true)}
      ${field("MP", `${basePath}.mp`, record.mp ?? 8, false, true)}
      ${field("Max MP", `${basePath}.max_mp`, record.max_mp ?? 8, false, true)}
      ${field("SP", `${basePath}.sp`, record.sp ?? 10, false, true)}
      ${field("Max SP", `${basePath}.max_sp`, record.max_sp ?? 10, false, true)}
      ${field("GOLD", `${basePath}.gold`, record.gold ?? 0, false, true)}
    </div>
    <h3 class="section-title">能力值</h3>
    <div class="form-grid attr-grid">
      ${attrInputs || '<p class="summary-line">请先在「属性定义」中添加属性。</p>'}
    </div>
    <h3 class="section-title">初始背包</h3>
    <div class="line-list">${inventoryRows}</div>
    <button data-add-inv="${basePath}.inventory" type="button">添加道具</button>
    <h3 class="section-title">初始装备</h3>
    <div class="line-list">${equipRows}</div>
    <button data-add-eq="${basePath}.equipment" type="button">添加装备</button>
    <h3 class="section-title">技能</h3>
    <div class="line-list">${skillsMarkup(basePath, record)}</div>
    <button data-add-skill="${basePath}.skills" type="button">添加技能</button>
    <button class="danger" data-remove-record="characters" data-index="${state.selectedIndex}" type="button" style="margin-top:16px">删除角色</button>
  </div>`;
}

function renderEnemiesEditor() {
  const records = state.scenario.enemies || [];
  const record = records[state.selectedIndex];
  if (!record) {
    els.editorPane.innerHTML = `<div class="editor-form"><p class="summary-line">还没有敌人。</p></div>`;
    return;
  }
  const basePath = `enemies.${state.selectedIndex}`;
  const attrDefs = state.scenario.attribute_defs || [];
  const attrs = record.attributes || {};
  const attrInputs = attrDefs.map((def) => {
    const attrId = def.id || "";
    const attrName = def.name || attrId || "";
    const value = attrs[attrId] ?? def.initial_value ?? 8;
    return field(attrName, `${basePath}.attributes.${escapeHtml(attrId)}`, value, false, true);
  }).join("");

  els.editorPane.innerHTML = `<div class="editor-form">
    <h2>${escapeHtml(record.name || record.id || "新敌人")}</h2>
    <div class="form-grid">
      ${field("ID", `${basePath}.id`, record.id || "")}
      ${field("名称", `${basePath}.name`, record.name || "")}
      <label class="wide">描述<textarea data-path="${basePath}.description">${escapeHtml(record.description || "")}</textarea></label>
      ${field("头像路径", `${basePath}.image`, record.image || "")}
    </div>
    <h3 class="section-title">基本属性</h3>
    <div class="form-grid">
      ${field("HP", `${basePath}.hp`, record.hp ?? 10, false, true)}
      ${field("Max HP", `${basePath}.max_hp`, record.max_hp ?? 10, false, true)}
      ${field("MP", `${basePath}.mp`, record.mp ?? 0, false, true)}
      ${field("Max MP", `${basePath}.max_mp`, record.max_mp ?? 0, false, true)}
      ${field("SP", `${basePath}.sp`, record.sp ?? 0, false, true)}
      ${field("Max SP", `${basePath}.max_sp`, record.max_sp ?? 0, false, true)}
    </div>
    <h3 class="section-title">能力值</h3>
    <div class="form-grid attr-grid">
      ${attrInputs || '<p class="summary-line">请先在「属性定义」中添加属性。</p>'}
    </div>
    <h3 class="section-title">技能</h3>
    <div class="line-list">${skillsMarkup(basePath, record)}</div>
    <button data-add-skill="${basePath}.skills" type="button">添加技能</button>
    <button class="danger" data-remove-record="enemies" data-index="${state.selectedIndex}" type="button" style="margin-top:16px">删除敌人</button>
  </div>`;
}

function renderChoices(path, choices, title) {
  els.editorPane.innerHTML = `<div class="editor-form">
    <h2>${escapeHtml(title)}</h2>
    ${choicesMarkup(path, choices)}
  </div>`;
}

function renderHybridEditor() {
  const location = state.scenario.locations[state.selectedIndex];
  if (!location) {
    els.editorPane.innerHTML = `<div class="editor-form"><p class="summary-line">No location selected.</p></div>`;
    return;
  }
  ensureHybridShape(location);
  const basePath = `locations.${state.selectedIndex}.hybrid`;
  const turns = location.hybrid.prepared_turns || [];
  els.editorPane.innerHTML = `<div class="editor-form">
    <h2>Hybrid prepared turns · ${escapeHtml(location.title || location.id || "")}</h2>
    <div class="form-grid">
      ${field("Mode", `${basePath}.mode`, location.hybrid.mode || "prepared_gm_turns")}
      <label class="wide">Summary<textarea data-path="${basePath}.summary">${escapeHtml(location.hybrid.summary || "")}</textarea></label>
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
      ${field("Action ID", `${path}.action_id`, turn.action_id || "")}
      ${field("Outcome", `${path}.outcome`, turn.outcome || "neutral")}
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

function actionsJsonMarkup(path, actions) {
  return `<h3 class="section-title">Actions</h3>
    <label class="wide">Action Graph JSON<textarea data-json-path="${path}" spellcheck="false">${escapeHtml(JSON.stringify(actions || [], null, 2))}</textarea></label>`;
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
  if (target.dataset.invPath) {
    const items = getByPath(state.scenario, target.dataset.invPath, []);
    const idx = Number(target.dataset.index);
    if (items[idx]) {
      let val = target.value;
      if (target.dataset.invField === "quantity") {
        const parsed = Number(val);
        val = Number.isFinite(parsed) ? parsed : val;
      }
      items[idx][target.dataset.invField] = val;
      markDirty();
    }
  }
  if (target.dataset.eqPath) {
    const eqs = getByPath(state.scenario, target.dataset.eqPath, []);
    eqs[Number(target.dataset.index)] = target.value;
    markDirty();
  }
  if (target.dataset.choicePath) {
    const choices = getByPath(state.scenario, target.dataset.choicePath, []);
    if (target.dataset.childIndex !== undefined) {
      const parentIdx = Number(target.dataset.index);
      const childIdx = Number(target.dataset.childIndex);
      const parent = choices[parentIdx];
      if (parent && Array.isArray(parent.children) && parent.children[childIdx]) {
        parent.children[childIdx][target.dataset.choiceField] = target.value;
      }
    } else {
      const choice = choices[Number(target.dataset.index)];
      choice[target.dataset.choiceField] = target.value;
    }
    markDirty();
  }
  if (target.dataset.relationPath) {
    const values = getByPath(state.scenario, target.dataset.relationPath, []);
    setByPath(state.scenario, target.dataset.relationPath, values);
    values[Number(target.dataset.index)] = target.value;
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
  if (target.dataset.removeChildChoice) {
    const choices = getByPath(state.scenario, target.dataset.removeChildChoice, []);
    const parent = choices[Number(target.dataset.parentIndex)];
    if (parent && Array.isArray(parent.children)) {
      parent.children.splice(Number(target.dataset.childIndex), 1);
      if (parent.children.length === 0) delete parent.children;
    }
    markDirty();
    renderEditor();
  }
  if (target.dataset.addChildChoice) {
    const choices = getByPath(state.scenario, target.dataset.addChildChoice, []);
    const parent = choices[Number(target.dataset.parentIndex)];
    if (parent) {
      if (!Array.isArray(parent.children)) parent.children = [];
      parent.children.push({ text: "", preview: "", risk: "" });
    }
    markDirty();
    renderEditor();
  }
  if (target.dataset.toggleChildren) {
    const choices = getByPath(state.scenario, target.dataset.toggleChildren, []);
    const parent = choices[Number(target.dataset.index)];
    if (parent) {
      if (Array.isArray(parent.children) && parent.children.length > 0) {
        delete parent.children;
      } else {
        parent.children = [{ text: "", preview: "", risk: "" }];
      }
      markDirty();
      renderEditor();
    }
  }
  if (target.dataset.removeChoice) {
    const choices = getByPath(state.scenario, target.dataset.removeChoice, []);
    choices.splice(Number(target.dataset.index), 1);
    markDirty();
    renderEditor();
  }
  if (target.dataset.addRelation) {
    const values = getByPath(state.scenario, target.dataset.addRelation, []);
    setByPath(state.scenario, target.dataset.addRelation, values);
    values.push("");
    markDirty();
    renderEditor();
  }
  if (target.dataset.removeRelation) {
    const values = getByPath(state.scenario, target.dataset.removeRelation, []);
    values.splice(Number(target.dataset.index), 1);
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
  if (target.dataset.addInv) {
    const items = getByPath(state.scenario, target.dataset.addInv, []);
    setByPath(state.scenario, target.dataset.addInv, items);
    items.push({ name: "", description: "", effect: "", quantity: 1 });
    markDirty();
    renderEditor();
  }
  if (target.dataset.removeInv) {
    const items = getByPath(state.scenario, target.dataset.removeInv, []);
    items.splice(Number(target.dataset.index), 1);
    markDirty();
    renderEditor();
  }
  if (target.dataset.addEq) {
    const eqs = getByPath(state.scenario, target.dataset.addEq, []);
    setByPath(state.scenario, target.dataset.addEq, eqs);
    eqs.push("");
    markDirty();
    renderEditor();
  }
  if (target.dataset.removeEq) {
    const eqs = getByPath(state.scenario, target.dataset.removeEq, []);
    eqs.splice(Number(target.dataset.index), 1);
    markDirty();
    renderEditor();
  }
  if (target.dataset.addSkill) {
    const skills = getByPath(state.scenario, target.dataset.addSkill, []);
    setByPath(state.scenario, target.dataset.addSkill, skills);
    skills.push({ name: "", description: "", effect: "", dice_type: "", cost: 0, cost_type: "" });
    markDirty();
    renderEditor();
  }
  if (target.dataset.removeSkill) {
    const skills = getByPath(state.scenario, target.dataset.removeSkill, []);
    skills.splice(Number(target.dataset.index), 1);
    markDirty();
    renderEditor();
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
    Object.assign(record, { goals: [], location_ids: [], next_scene_ids: [] });
  }
  if (section === "locations") {
    Object.assign(record, { npc_ids: [], item_ids: [], clue_ids: [], enemy_ids: [], connected_location_ids: [], choices: [] });
  }
  if (section === "attribute_defs") {
    record.initial_value = 8;
  }
  if (section === "characters") {
    Object.assign(record, {
      default_name: "",
      description: "",
      image: "",
      image_female: "",
      hp: 20, max_hp: 20,
      mp: 8, max_mp: 8,
      sp: 10, max_sp: 10,
      gold: 0,
      attributes: {},
      inventory: [],
      equipment: [],
      skills: [],
    });
  }
  if (section === "enemies") {
    Object.assign(record, {
      description: "",
      image: "",
      hp: 10, max_hp: 10,
      mp: 0, max_mp: 0,
      sp: 0, max_sp: 0,
      attributes: {},
      skills: [],
    });
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
  scenario.attribute_defs.forEach((def) => {
    if (def.initial_value == null) def.initial_value = 8;
  });
  scenario.characters.forEach((char) => {
    char.default_name ||= "";
    char.description ||= "";
    char.image ||= "";
    char.image_female ||= "";
    char.hp = Number.isFinite(Number(char.hp)) ? Number(char.hp) : 20;
    char.max_hp = Number.isFinite(Number(char.max_hp)) ? Number(char.max_hp) : char.hp;
    char.mp = Number.isFinite(Number(char.mp)) ? Number(char.mp) : 8;
    char.max_mp = Number.isFinite(Number(char.max_mp)) ? Number(char.max_mp) : char.mp;
    char.sp = Number.isFinite(Number(char.sp)) ? Number(char.sp) : 10;
    char.max_sp = Number.isFinite(Number(char.max_sp)) ? Number(char.max_sp) : char.sp;
    char.gold = Number.isFinite(Number(char.gold)) ? Number(char.gold) : 0;
    char.attributes = char.attributes && typeof char.attributes === "object" ? char.attributes : {};
    char.inventory = Array.isArray(char.inventory) ? char.inventory : [];
    char.equipment = Array.isArray(char.equipment) ? char.equipment : [];
    char.skills = Array.isArray(char.skills) ? char.skills : [];
  });
  scenario.enemies.forEach((enemy) => {
    enemy.description ||= "";
    enemy.image ||= "";
    enemy.hp = Number.isFinite(Number(enemy.hp)) ? Number(enemy.hp) : 10;
    enemy.max_hp = Number.isFinite(Number(enemy.max_hp)) ? Number(enemy.max_hp) : enemy.hp;
    enemy.mp = Number.isFinite(Number(enemy.mp)) ? Number(enemy.mp) : 0;
    enemy.max_mp = Number.isFinite(Number(enemy.max_mp)) ? Number(enemy.max_mp) : enemy.mp;
    enemy.sp = Number.isFinite(Number(enemy.sp)) ? Number(enemy.sp) : 0;
    enemy.max_sp = Number.isFinite(Number(enemy.max_sp)) ? Number(enemy.max_sp) : enemy.sp;
    enemy.attributes = enemy.attributes && typeof enemy.attributes === "object" ? enemy.attributes : {};
    enemy.skills = Array.isArray(enemy.skills) ? enemy.skills : [];
  });
  if (!scenario.scenes.length) {
    scenario.scenes.push({ id: "start", title: "开始", description: "", keywords: [], goals: [] });
  }
  scenario.meta.initial_scene ||= scenario.scenes[0].id || "start";
  scenario.fallback_choices = normalizeChoices(scenario.fallback_choices);
  scenario.combat_choices = normalizeChoices(scenario.combat_choices);
  scenario.scenes.forEach((scene) => {
    scene.goals = Array.isArray(scene.goals) ? scene.goals : [];
    scene.location_ids = Array.isArray(scene.location_ids) ? scene.location_ids : [];
    scene.next_scene_ids = Array.isArray(scene.next_scene_ids) ? scene.next_scene_ids : [];
    scene.actions = normalizeActions(scene.actions);
  });
  scenario.locations.forEach((location) => {
    location.npc_ids = Array.isArray(location.npc_ids) ? location.npc_ids : [];
    location.item_ids = Array.isArray(location.item_ids) ? location.item_ids : [];
    location.clue_ids = Array.isArray(location.clue_ids) ? location.clue_ids : [];
    location.enemy_ids = Array.isArray(location.enemy_ids) ? location.enemy_ids : [];
    location.connected_location_ids = Array.isArray(location.connected_location_ids) ? location.connected_location_ids : [];
    location.choices = normalizeChoices(location.choices);
    location.actions = normalizeActions(location.actions);
    if (location.hybrid) ensureHybridShape(location);
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
    turn.action_id ||= "";
    turn.outcome ||= "";
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
    action_id: "",
    outcome: "",
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
      const normalized = {
        ...(choice?.id ? { id: choice.id } : {}),
        ...(choice?.action_id ? { action_id: choice.action_id } : {}),
        text: choice?.text || "",
        preview: choice?.preview || "",
        risk: choice?.risk || "",
      };
      for (const key of ["intent_keywords", "requirements", "roll", "effects", "success_effects", "failure_effects", "once", "disabled_after", "prepared_turn_id"]) {
        if (choice && choice[key] !== undefined) normalized[key] = choice[key];
      }
      if (Array.isArray(choice?.children) && choice.children.length > 0) {
        normalized.children = normalizeChoices(choice.children);
      }
      return normalized;
    });
}

function normalizeActions(value) {
  if (!Array.isArray(value)) return [];
  return value
    .filter((action) => action && typeof action === "object")
    .map((action, index) => ({
      ...action,
      id: action.id || action.action_id || `action_${index + 1}`,
      text: action.text || action.label || "",
      preview: action.preview || "",
      risk: action.risk || "",
      intent_keywords: Array.isArray(action.intent_keywords) ? action.intent_keywords : [],
    }));
}

function syncInitialSceneAfterIdEdit() {
  const ids = state.scenario.scenes.map((scene) => scene.id);
  if (!ids.includes(state.scenario.meta.initial_scene)) {
    state.scenario.meta.initial_scene = ids[0] || "start";
  }
}

function choicesMarkup(path, choices) {
  return `<div class="line-list">
    ${choices.map((choice, index) => {
      const hasChildren = Array.isArray(choice.children) && choice.children.length > 0;
      const childMarkup = hasChildren
        ? `<div class="choice-children">
            ${choice.children.map((child, ci) => `<div class="choice-row choice-child">
              <input data-choice-path="${path}" data-choice-field="text" data-index="${index}" data-child-index="${ci}" value="${escapeAttr(child.text || "")}" placeholder="子选项 text" />
              <input data-choice-path="${path}" data-choice-field="preview" data-index="${index}" data-child-index="${ci}" value="${escapeAttr(child.preview || "")}" placeholder="子选项 preview" />
              <input data-choice-path="${path}" data-choice-field="risk" data-index="${index}" data-child-index="${ci}" value="${escapeAttr(child.risk || "")}" placeholder="子选项 risk" />
              <button class="danger" data-remove-child-choice="${path}" data-parent-index="${index}" data-child-index="${ci}" type="button">删除</button>
            </div>`).join("")}
            <button data-add-child-choice="${path}" data-parent-index="${index}" type="button">添加子选项</button>
          </div>`
        : "";
      const childToggle = `<button class="toggle-children" data-toggle-children="${path}" data-index="${index}" type="button">${hasChildren ? "收起子选项" : "添加子选项"}</button>`;
      return `<div class="choice-group">
        <div class="choice-row">
          <input data-choice-path="${path}" data-choice-field="text" data-index="${index}" value="${escapeAttr(choice.text || "")}" placeholder="text" />
          <input data-choice-path="${path}" data-choice-field="preview" data-index="${index}" value="${escapeAttr(choice.preview || "")}" placeholder="preview" />
          <input data-choice-path="${path}" data-choice-field="risk" data-index="${index}" value="${escapeAttr(choice.risk || "")}" placeholder="risk" />
          ${childToggle}
          <button class="danger" data-remove-choice="${path}" data-index="${index}" type="button">删除</button>
        </div>
        ${hasChildren ? childMarkup : `<div class="choice-children collapsed" data-children-path="${path}" data-children-index="${index}"></div>`}
      </div>`;
    }).join("")}
    <button data-add-choice="${path}" type="button">添加选项</button>
  </div>`;
}

function relationPicker(label, path, selectedIds, records) {
  const values = Array.isArray(selectedIds) ? selectedIds : [];
  const rows = values.length
    ? values.map((value, index) => relationRow(label, path, value, index, records)).join("")
    : `<p class="summary-line">未关联${escapeHtml(label)}。</p>`;
  return `<section class="relation-picker">
    <div class="relation-picker-head">
      <h4>${escapeHtml(label)}</h4>
      <button data-add-relation="${path}" type="button">添加</button>
    </div>
    <div class="relation-rows">${rows}</div>
  </section>`;
}

function relationRow(label, path, value, index, records) {
  const current = String(value || "");
  const options = (records || [])
    .filter((record) => record && record.id)
    .map((record) => {
      const id = String(record.id);
      return `<option value="${escapeAttr(id)}" ${id === current ? "selected" : ""}>${escapeHtml(recordOptionLabel(record))}</option>`;
    })
    .join("");
  const missing = current && !(records || []).some((record) => String(record?.id || "") === current)
    ? `<option value="${escapeAttr(current)}" selected>${escapeHtml(current)} (missing)</option>`
    : "";
  return `<div class="relation-row">
    <select data-relation-path="${path}" data-index="${index}" aria-label="${escapeAttr(label)}">${missing}<option value="">未选择</option>${options}</select>
    <button class="danger" data-remove-relation="${path}" data-index="${index}" type="button">删除</button>
  </div>`;
}

function recordOptionLabel(record) {
  const id = String(record.id || "");
  const title = record.title || record.name || id;
  return title && title !== id ? `${title} (${id})` : id;
}

function skillsMarkup(basePath, record) {
  const skills = record.skills || [];
  return skills.map((skill, si) => `<div class="skill-card">
    <div class="skill-card-head">
      <strong>技能 ${si + 1}</strong>
      <button class="danger" data-remove-skill="${basePath}.skills" data-index="${si}" type="button">删除</button>
    </div>
    <div class="form-grid">
      ${field("名称", `${basePath}.skills.${si}.name`, skill.name || "", false)}
      ${field("消耗", `${basePath}.skills.${si}.cost`, skill.cost ?? 0, false, true)}
      ${field("消耗类型", `${basePath}.skills.${si}.cost_type`, skill.cost_type || "")}
      <label class="wide">描述<textarea data-path="${basePath}.skills.${si}.description">${escapeHtml(skill.description || "")}</textarea></label>
      <label class="wide">效果<textarea data-path="${basePath}.skills.${si}.effect">${escapeHtml(skill.effect || "")}</textarea></label>
      ${field("骰子类型", `${basePath}.skills.${si}.dice_type`, skill.dice_type || "")}
    </div>
  </div>`).join("");
}

function field(label, path, value, csv = false, number = false) {
  return `<label>${escapeHtml(label)}<input data-path="${path}" data-csv="${csv ? "true" : "false"}" data-number="${number ? "true" : "false"}" value="${escapeAttr(value)}" /></label>`;
}

function sectionLabel(section) {
  return ({ meta: "基本信息", rules: "规则", hybrid: "Hybrid", fallback: "全局选项", combat: "战斗选项", json: "JSON", attribute_defs: "属性定义", characters: "角色", enemies: "敌人" })[section] || section;
}

function summaryForSection(section) {
  if (section === "meta") return "编辑标题、摘要、语言和起始场景。";
  if (section === "rules") return `${state.scenario.rules.length} 条规则`;
  if (section === "hybrid") return `${state.scenario.locations.length} locations with editable prepared turns`;
  if (section === "fallback") return `${state.scenario.fallback_choices.length} 个全局选项`;
  if (section === "combat") return `${state.scenario.combat_choices.length} 个战斗选项`;
  if (section === "attribute_defs") return `${state.scenario.attribute_defs.length} 个属性定义`;
  if (section === "characters") return `${state.scenario.characters.length} 个角色`;
  if (section === "enemies") return `${state.scenario.enemies.length} 个敌人`;
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
