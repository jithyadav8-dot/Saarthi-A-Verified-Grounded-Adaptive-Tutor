import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import Module, { createRequire } from "node:module";
import { test } from "node:test";
import React from "react";
import ts from "typescript";

const require = createRequire(import.meta.url);
const blank = () => null;
const components = new Proxy({}, {get: (_, name) => name === "__esModule" ? true : blank});

// Run the real component callbacks with controlled hooks/API promises. This
// checks transitions without browser layout, scheduling, or event propagation.
function harness(path, exportName, api, props = {}) {
  const slots = [];
  let cursor = 0;
  let effects = [];
  const changed = (old, next) => !old || !next || old.some((v, i) => !Object.is(v, next[i]));
  const react = {...React,
    useState(initial) {
      const index = cursor++;
      if (!(index in slots)) slots[index] = typeof initial === "function" ? initial() : initial;
      return [slots[index], value => {slots[index] = typeof value === "function" ? value(slots[index]) : value;}];
    },
    useRef(initial) {
      const index = cursor++;
      return slots[index] ??= {current: initial};
    },
    useCallback(callback, deps) {
      const index = cursor++;
      if (changed(slots[index]?.deps, deps)) slots[index] = {callback, deps};
      return slots[index].callback;
    },
    useEffect(callback, deps) {
      const index = cursor++;
      if (changed(slots[index], deps)) effects.push(callback);
      slots[index] = deps;
    },
  };
  const filename = fileURLToPath(new URL(path, import.meta.url));
  const loaded = new Module(filename);
  loaded.require = id => {
    if (id === "react") return react;
    if (id === "next/link") return "a";
    if (id === "lucide-react" || id.startsWith("@/components/")) return components;
    if (id === "@/lib/api") return api;
    if (id === "@/lib/mockData") return {};
    return require(id);
  };
  loaded._compile(ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true},
  }).outputText, filename);
  return {
    render() {cursor = 0; return loaded.exports[exportName](props);},
    async flush() {
      const pending = effects;
      effects = [];
      for (const effect of pending) effect();
      await new Promise(resolve => setImmediate(resolve));
    },
  };
}

function nodes(tree) {
  if (!tree || typeof tree !== "object") return [];
  if (Array.isArray(tree)) return tree.flatMap(nodes);
  return [tree, ...nodes(tree.props?.children)];
}
function textOf(tree) {
  if (tree == null || typeof tree === "boolean") return "";
  if (typeof tree !== "object") return String(tree);
  if (Array.isArray(tree)) return tree.map(textOf).join(" ");
  return textOf(tree.props?.children);
}
const session = {id: "s1", title: "Saved chat", updated_at: new Date().toISOString()};

test("a missed source term shows its quote and becomes the next practice round", async () => {
  const card = {item_id: "abc", prompt: "_____ equals mass times velocity.", location: "p. 1"};
  const h = harness("../components/SourcePractice.tsx", "SourcePractice", {
    listPracticeSources: async () => ({sources: ["notes.md"]}),
    loadRecallCards: async () => ({cards: [card]}),
    checkRecall: async (source, item, answer) => {
      assert.deepEqual([source, item, answer], ["notes.md", "abc", "force"]);
      return {matches: false, term: "Momentum", citation: {source_id: source, label: "p. 1", excerpt: "Momentum equals mass times velocity."}};
    },
  });
  h.render(); await h.flush();
  nodes(h.render()).find(node => node.props?.id === "recall-term").props.onChange({target: {value: "force"}});
  await nodes(h.render()).find(node => node.type === "form").props.onSubmit({preventDefault() {}});
  assert.match(textOf(h.render()), /Momentum equals mass times velocity/);
  const oldFrame = globalThis.requestAnimationFrame;
  globalThis.requestAnimationFrame = callback => callback();
  try {
    nodes(h.render()).find(node => node.type === "button" && textOf(node).includes("Finish round")).props.onClick();
  } finally { if (oldFrame) globalThis.requestAnimationFrame = oldFrame; else delete globalThis.requestAnimationFrame; }
  const finished = h.render();
  assert.match(textOf(finished).replace(/\s+/g, " "), /0 of 1 source terms recalled/);
  nodes(finished).find(node => node.type === "button" && textOf(node).includes("Practice missed terms")).props.onClick();
  assert.match(textOf(h.render()), /Which term completes/);
});
const sidebarProps = {currentSessionId: "s1", isCollapsed: false, onSessionSelect() {}, onNewChat() {}};

test("failed chat-history load ends loading and offers a retry", async () => {
  let fail = true;
  const h = harness("../components/ChatSidebar.tsx", "ChatSidebar", {
    listSessions: async () => {if (fail) throw new Error("History offline"); return [session];},
    fetchCompletedQuizzes: async () => [],
  }, sidebarProps);
  h.render(); await h.flush();
  let tree = h.render();
  assert.match(textOf(tree), /History offline/);
  assert.ok(!nodes(tree).some(n => n.props?.className?.includes("animate-pulse")));
  const retry = nodes(tree).find(n => n.type === "button" && textOf(n).includes("Retry loading history"));
  fail = false;
  await retry.props.onClick();
  tree = h.render();
  assert.match(textOf(tree), /Saved chat/);
  assert.doesNotMatch(textOf(tree), /History offline/);
});

test("failed chat creation never selects a fabricated session", async () => {
  const created = [];
  const h = harness("../components/ChatSidebar.tsx", "ChatSidebar", {
    createSession: async () => {throw new Error("Creation offline");},
  }, {...sidebarProps, onNewChat: value => created.push(value)});
  const button = nodes(h.render()).find(n => n.props?.id === "new-chat-btn");
  await button.props.onClick();
  const tree = h.render();
  assert.deepEqual(created, []);
  assert.match(textOf(tree), /Creation offline/);
  assert.equal(nodes(tree).find(n => n.props?.id === "new-chat-btn").props.disabled, false);
});

test("failed deletion preserves the session and permits a successful retry", async () => {
  let fail = true;
  const deleted = [];
  const h = harness("../components/ChatSidebar.tsx", "ChatSidebar", {
    listSessions: async () => [session], fetchCompletedQuizzes: async () => [],
    deleteSession: async () => {if (fail) throw new Error("Delete offline");},
  }, {...sidebarProps, onSessionDeleted: id => deleted.push(id)});
  h.render(); await h.flush();
  const clickDelete = tree => nodes(tree).find(n => n.props?.title === "Delete chat").props.onClick({stopPropagation() {}});
  await clickDelete(h.render());
  let tree = h.render();
  assert.match(textOf(tree), /Saved chat/);
  assert.match(textOf(tree), /Delete offline/);
  assert.deepEqual(deleted, []);
  assert.ok(!nodes(tree).some(n => n.props?.className?.includes("pointer-events-none")));
  fail = false;
  await clickDelete(tree);
  tree = h.render();
  assert.doesNotMatch(textOf(tree), /Saved chat/);
  assert.deepEqual(deleted, ["s1"]);
});

test("an empty custom quiz replaces the previous questions and keeps filters available", async () => {
  let requests = 0;
  const question = {q_id: "q1", concept_id: "c1", topic: "Example", stem: "Prior question", options: [], verified: false};
  const h = harness("../app/quiz/page.tsx", "default", {
    fetchKnowledgeGraph: async () => ({nodes: []}), fetchStudentMastery: async () => ({board: []}),
    fetchAdaptiveQuiz: async () => ({questions: requests++ === 0 ? [question] : []}),
  });
  h.render(); await h.flush();
  let tree = h.render();
  assert.ok(nodes(tree).some(n => n.props?.activeQuestion?.q_id === "q1"));
  const generate = nodes(tree).find(n => n.type === "button" && textOf(n).includes("Generate Custom Quiz"));
  await generate.props.onClick();
  tree = h.render();
  assert.ok(!nodes(tree).some(n => n.props?.activeQuestion));
  assert.match(textOf(tree), /No questions are available/);
  assert.ok(nodes(tree).some(n => n.type === "select"));
});
