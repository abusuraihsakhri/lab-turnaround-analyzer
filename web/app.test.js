"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const { analyzeCSV, parseCSV, annotatedCSV, EXAMPLE } = require("./app.js");

test("example metrics match Python reference", () => {
  const result = analyzeCSV(EXAMPLE, 60);
  assert.equal(result.overall.count, 5);
  assert.equal(result.overall.breach_count, 3);
  assert.equal(result.overall.breach_rate_pct, 60);
  assert.equal(result.by_test.CBC.p50_minutes, 75);
  assert.equal(result.by_test.CBC.p90_minutes, 195);
  assert.equal(result.by_test.CRP.mean_minutes, 80);
});
test("outlier rule requires four records per analyte", () => {
  const header = "test,received_at,reported_at\n";
  const rows = [10, 10, 10, 10, 100].map(m => "X,2026-01-01T00:00:00Z,2026-01-01T" + String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0") + ":00Z");
  assert.equal(analyzeCSV(header + rows.join("\n")).overall.outlier_count, 1);
});
test("quoted fields and CRLF parse without executing markup", () => {
  const csv = 'test,received_at,reported_at,note\r\n"CRP, serial",2026-01-01T00:00:00Z,2026-01-01T00:10:00Z,"<img src=x onerror=alert(1)>"\r\n';
  const result = analyzeCSV(csv);
  assert.equal(result.records[0].test, "CRP, serial");
  assert.match(annotatedCSV(result), /<img src=x/);
});
test("formula injection is neutralized on export", () => {
  const csv = 'test,received_at,reported_at,note\nCBC,2026-01-01T00:00:00Z,2026-01-01T00:20:00Z,"=SUM(1,2)"';
  assert.match(annotatedCSV(analyzeCSV(csv)), /"'=SUM\(1,2\)"/);
});
test("rejects invalid timestamps and schema", () => {
  const prefix = "test,received_at,reported_at\n";
  assert.throws(() => analyzeCSV(prefix + "A,2026-02-30T00:00:00Z,2026-03-01T00:00:00Z"), /invalid/);
  assert.throws(() => analyzeCSV(prefix + "A,2026-01-01T00:00:00Z,2025-12-31T23:00:00Z"), /precedes/);
  assert.throws(() => analyzeCSV(prefix + "A,2026-01-01T00:00:00,2026-01-01T01:00:00Z"), /ISO 8601/);
  assert.throws(() => analyzeCSV("test,test,received_at,reported_at\n"), /duplicate/);
  assert.throws(() => analyzeCSV(prefix + "A,2026-01-01T00:00:00Z"), /column count/);
  assert.throws(() => parseCSV(prefix + '"unterminated'), /Unterminated/);
  assert.throws(() => analyzeCSV(EXAMPLE, 0), /positive/);
});

test("CSV header formulas are escaped too", () => {
  const csv = "test,received_at,reported_at,=2+2\nCBC,2026-01-01T00:00:00Z,2026-01-01T00:20:00Z,ok";
  assert.match(annotatedCSV(analyzeCSV(csv)).split("\r\n")[0], /"'=2\+2"/);
});
