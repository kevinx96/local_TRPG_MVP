// Offline event-handler test. This is a minimal DOM, not a rendering/browser test.
"use strict";
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const html = fs.readFileSync(process.argv[2], "utf8");
const embedded = html.match(/<script id="payload" type="application\/json">([\s\S]*?)<\/script>/)[1];
const payload = JSON.parse(embedded);
const script = html.match(/<\/script><script>([\s\S]*?)<\/script>/)[1];
class Element {
  constructor(tag = "div") { this.tag = tag; this.value = ""; this.children = []; this.textContent = ""; this.hidden = false; this.checked = false; }
  replaceChildren(...children) { this.children = children; this.value = ""; }
  append(...children) { this.children.push(...children); }
  click() { if (this.onclick) this.onclick(); }
}
const elements = new Map();
const get = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
get("payload").textContent = embedded;
const storage = new Map();
let exported;
const sandbox = {
  document: {getElementById: get, createElement: tag => new Element(tag)},
  localStorage: {getItem: key => storage.get(key) || null, setItem: (key, value) => storage.set(key, value)},
  Blob: class { constructor(parts) { this.parts = parts; } },
  URL: {createObjectURL: blob => {exported = JSON.parse(blob.parts.join("")); return "blob:fixture";}, revokeObjectURL: () => {}},
  setTimeout: fn => fn(),
};
vm.runInNewContext(script, sandbox);
assert.match(get("progress").textContent, /1 \/ 50/);
get("save").click();
assert.match(get("notice").textContent, /注釈者 ID/);
get("annotator").value = "offline-fixture";
get("load").click();
get("kind").value = "dialogue";
get("kind").onchange();
assert.equal(get("actionRow").hidden, true);
assert.equal(get("operationRow").hidden, true);
get("save").click();
assert.match(get("progress").textContent, /保存済み 1/);
get("next").click();
assert.match(get("progress").textContent, /2 \/ 50/);
get("load").click(); // Restore the saved first-item progress.
assert.equal(get("kind").value, "dialogue");
get("kind").value = "interact";
get("kind").onchange();
assert.equal(get("operationRow").hidden, false);
get("operation").value = "sneak";
get("target_id").value = "forest_slime";
get("advance").checked = true;
get("save").click();
get("export").click();
assert.equal(exported.complete, false);
assert.equal(exported.sample_sha256, payload.sample_sha256);
assert.equal(exported.answers[0].plan.advance, true);
assert.equal(exported.answers[0].plan.operation, "sneak");
const actionIndex = payload.cases.findIndex(row => row.context.actions.length);
get("jump").value = String(actionIndex);
get("jump").onchange();
get("kind").value = "existing";
get("kind").onchange();
assert.equal(get("actionRow").hidden, false);
assert.equal(get("targetRow").hidden, true);
get("action_id").value = payload.cases[actionIndex].context.actions[0].id;
get("save").click();
get("export").click();
const existing = exported.answers.find(row => row.id === payload.cases[actionIndex].id).plan;
assert.equal(existing.operation, "");
assert.equal(existing.item_id, "");
assert.equal(existing.advance, false);
get("annotator").value = "another-fixture";
get("load").click();
assert.match(get("progress").textContent, /保存済み 0/);
console.log("IAA handler smoke: save, restore, navigation, kind fields, export and annotator isolation OK");
