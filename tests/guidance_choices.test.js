const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

class Element {
  constructor() {
    this.children = [];
    this.dataset = {};
    this.style = {};
    this.attributes = {};
    this.classes = new Set();
    this.classList = {
      toggle: (name, value) => value ? this.classes.add(name) : this.classes.delete(name),
      remove: name => this.classes.delete(name),
    };
  }
  setAttribute(name, value) { this.attributes[name] = value; }
  appendChild(child) { this.children.push(child); }
  append(child) { this.appendChild(child); }
  prepend(child) { this.children.unshift(child); }
  querySelector() { return this.children[0]; }
}
const els = { choicesList: new Element(), choicesArea: new Element(), dialogueBox: new Element() };
const source = fs.readFileSync("client/app.js", "utf8");
const start = source.indexOf("function renderChoices(");
const end = source.indexOf("function highlightChoice(", start);
const context = {
  document: { createElement: () => new Element() }, els, state: {choiceStack: []},
  choiceDebug() {}, choiceLayoutDebug() {}, highlightChoice() {}, hideChoices() {},
  isCombatChoice: () => false, classifyRisk: () => "safe", rubyHtml: text => text,
};
vm.createContext(context);
vm.runInContext(source.slice(start, end), context);
context.renderChoices([
  {text: "討伐を報告する", guidance: true},
  {text: "討伐を報告する"},
  {text: "討伐を報告する", guidance: true, enabled: false},
  {text: "？？？", guidance: true, visibility: "unknown", enabled: false},
]);
const [guided, ordinary, disabled, unknown] = els.choicesList.children;
assert(guided.classes.has("guidance-choice"));
assert.equal(guided.children[0].children[0].textContent, "★");
assert.equal(guided.children[0].children[0].attributes["aria-label"], "メイン");
assert.equal(guided.children[0].textContent, "1");
assert(!ordinary.classes.has("guidance-choice"));
assert(disabled.classes.has("guidance-choice"));
assert.equal(disabled.attributes["aria-disabled"], "true");
assert(!unknown.classes.has("guidance-choice"));
assert.equal(unknown.children[0].children.length, 0);
console.log("guidance choices: 4 rendering states passed");
