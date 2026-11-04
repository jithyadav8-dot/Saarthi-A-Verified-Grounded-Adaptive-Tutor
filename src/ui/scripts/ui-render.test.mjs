import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import Module, { createRequire } from "node:module";
import { test } from "node:test";
import React from "react";
import { renderToString } from "react-dom/server";
import ts from "typescript";

const require = createRequire(import.meta.url);
const emptyComponent = () => null;
const icons = new Proxy({}, {get: (_, key) => key === "__esModule" ? true : emptyComponent});

// Exercise real component rendering with server-returned fixtures, without a browser or providers.
function loadComponent(relativePath, stateOverrides = {}) {
  const filename = fileURLToPath(new URL(relativePath, import.meta.url));
  let stateIndex = 0;
  const reactShim = {...React, useState(initial) {
    const index = stateIndex++;
    return React.useState(Object.hasOwn(stateOverrides, index) ? stateOverrides[index] : initial);
  }};
  const loaded = new Module(filename);
  loaded.require = id => {
    if (id === "react") return reactShim;
    if (id === "lucide-react") return icons;
    if (id.startsWith("@/components/")) return icons;
    if (id === "@/lib/mockData") return {MOCK_CONCEPTS: [], MOCK_CONTENT_UNITS: []};
    if (id === "@/lib/api") return {getApiBaseUrl: () => "http://localhost:8000", getMaterialUrl: path => `http://localhost:8000${path}`};
    return require(id);
  };
  loaded._compile(ts.transpileModule(readFileSync(filename, "utf8"), {
    compilerOptions: {module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true},
  }).outputText, filename);
  return loaded.exports;
}

const missingEvidenceConcept = {
  concept_id: "c-curated", name: "Curated topic", topic: "Demo", prerequisites: [],
  evidence_units: ["missing-unit"], evidence_details: [], mastery: 0, masteryKnown: false, status: "unvisited",
};

test("a graph node with missing evidence renders an unavailable notice", () => {
  const {default: GraphPage} = loadComponent("../app/graph/page.tsx", {0: [missingEvidenceConcept], 1: missingEvidenceConcept});
  const html = renderToString(React.createElement(GraphPage));
  assert.match(html, /Evidence unavailable/);
  assert.doesNotMatch(html, /undefined|NaN/);
});

test("graph mastery is labelled unknown until an actual learner value exists", () => {
  const {PrerequisiteGraph} = loadComponent("../components/PrerequisiteGraph.tsx");
  const html = renderToString(React.createElement(PrerequisiteGraph, {
    concepts: [missingEvidenceConcept], selectedConcept: missingEvidenceConcept, onSelectConcept() {},
  }));
  assert.match(html, /Not measured/);
  assert.doesNotMatch(html, />0%/);
});

test("citation evidence never invents a measured faithfulness score", () => {
  const {CitationDrawer} = loadComponent("../components/CitationDrawer.tsx");
  const html = renderToString(React.createElement(CitationDrawer, {
    citation: {source: "notes.txt", label: "Page 1", location: {page: 1}, excerpt: "Actual source excerpt"}, onClose() {},
  }));
  assert.match(html, /Actual source excerpt/);
  assert.doesNotMatch(html, /Faithfulness Score: 1\.00|Verified Origin/);
});

test("measured mastery and actual source evidence remain visible", () => {
  const concept = {...missingEvidenceConcept, mastery: 0.37, masteryKnown: true,
    evidence_details: [{unit_id: "real-unit", source_id: "course.txt", location: {page: 2}, text: "Actual excerpt from the course"}]};
  const {default: GraphPage} = loadComponent("../app/graph/page.tsx", {0: [concept], 1: concept});
  const html = renderToString(React.createElement(GraphPage));
  assert.match(html, /37%/);
  assert.match(html, /Actual excerpt from the course/);
  assert.doesNotMatch(html, /Evidence unavailable|Not measured/);
});

test("unrelated consecutive concepts do not acquire a prerequisite edge", () => {
  const {PrerequisiteGraph} = loadComponent("../components/PrerequisiteGraph.tsx");
  const unrelated = {...missingEvidenceConcept, concept_id: "unrelated", name: "Unrelated topic"};
  const html = renderToString(React.createElement(PrerequisiteGraph, {
    concepts: [missingEvidenceConcept, unrelated], selectedConcept: missingEvidenceConcept, onSelectConcept() {},
  }));
  assert.doesNotMatch(html, /<span>prerequisite<\/span>/);
});

test("an actual consecutive prerequisite edge remains visible", () => {
  const {PrerequisiteGraph} = loadComponent("../components/PrerequisiteGraph.tsx");
  const dependent = {...missingEvidenceConcept, concept_id: "dependent", prerequisites: [missingEvidenceConcept.concept_id]};
  const html = renderToString(React.createElement(PrerequisiteGraph, {
    concepts: [missingEvidenceConcept, dependent], selectedConcept: missingEvidenceConcept, onSelectConcept() {},
  }));
  assert.match(html, /<span>prerequisite<\/span>/);
});

test("an unavailable graph shows an error instead of an illustrative curriculum", () => {
  const {default: GraphPage} = loadComponent("../app/graph/page.tsx", {2: "Service unavailable", 3: false});
  const html = renderToString(React.createElement(GraphPage));
  assert.match(html, /Service unavailable/);
  assert.match(html, /Retry loading graph/);
  assert.doesNotMatch(html, /Chain Rule|55%|65%|75%/);
});

test("an empty quiz finishes loading and retains the customization controls", () => {
  const {default: QuizPage} = loadComponent("../app/quiz/page.tsx", {9: false});
  const html = renderToString(React.createElement(QuizPage));
  assert.match(html, /No questions are available for this selection/);
  assert.match(html, /Number of Questions/);
  assert.match(html, /Generate/);
  assert.doesNotMatch(html, /Loading assessment questions/);
});
