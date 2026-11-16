import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import Module from "node:module";
import { test, afterEach } from "node:test";
import ts from "typescript";

const filename = fileURLToPath(new URL("../lib/api.ts", import.meta.url));
const compiled = ts.transpileModule(readFileSync(filename, "utf8"), {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
});
const loaded = new Module(filename);
loaded._compile(compiled.outputText, filename);
const api = loaded.exports;
const originalFetch = global.fetch;
afterEach(() => { global.fetch = originalFetch; });

test("failed uploads surface the backend error", async () => {
  global.fetch = async () => new Response(JSON.stringify({detail: "File exceeds upload limit"}), {status: 413});
  await assert.rejects(api.uploadCourseFiles([new File(["notes"], "notes.txt")]), /upload limit/);
});

test("a nominal success with no indexed content is rejected", async () => {
  global.fetch = async () => Response.json({status: "success", units_created: 0});
  await assert.rejects(api.uploadCourseFiles([new File([""], "empty.txt")]), /No searchable content/);
});

test("successful uploads preserve actual returned evidence", async () => {
  const result = {status: "success", units_created: 1, files_processed: 1,
    sample_units: [{unit_id: "u1", source_id: "notes.txt", location: {page: 3}, text: "Real text"}]};
  global.fetch = async () => Response.json(result);
  assert.deepEqual(await api.uploadCourseFiles([new File(["notes"], "notes.txt")]), result);
});

test("grading errors never become a correct-answer response", async () => {
  global.fetch = async () => new Response("Unavailable", {status: 503});
  await assert.rejects(api.submitStudentAnswer("student", "q1", "wrong"), /503/);
});

test("quiz preferences are sent without an answer key", async () => {
  global.fetch = async (url, init) => {
    assert.ok(url.endsWith("/quiz"));
    assert.deepEqual(JSON.parse(init.body), {student_id: "s1", size: 3, difficulty: 2, concept_id: "c-pca"});
    return Response.json({questions: []});
  };
  assert.deepEqual(await api.fetchAdaptiveQuiz("s1", 3, 2, "c-pca"), {questions: []});
});

test("session IDs are encoded in request paths", async () => {
  global.fetch = async url => {
    assert.ok(url.endsWith("/sessions/a%2Fb%3Fc"));
    return Response.json({messages: []});
  };
  await api.getSession("a/b?c");
});

test("answer submissions preserve the issued attempt for safe retries", async () => {
  global.fetch = async (url, init) => {
    assert.ok(url.endsWith("/answer"));
    assert.deepEqual(JSON.parse(init.body), {student_id: "s1", q_id: "q1", answer: "42", attempt_id: "attempt-1"});
    return Response.json({correct: true, replayed: true, new_mastery: .7});
  };
  assert.equal((await api.submitStudentAnswer("s1", "q1", "42", "attempt-1")).replayed, true);
});
