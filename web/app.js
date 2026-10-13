"use strict";

/* All analysis runs locally. No network requests or persistent storage. */
(function (root) {
  const MAX_CHARS = 2000000;
  const MAX_RECORDS = 20000;
  const REQUIRED = ["test", "received_at", "reported_at"];
  const EXAMPLE = [
    "test,received_at,reported_at,specimen_id",
    "CBC,2026-10-01T08:00:00Z,2026-10-01T08:30:00Z,S-001",
    "CBC,2026-10-01T08:00:00Z,2026-10-01T09:00:00Z,S-002",
    "CBC,2026-10-01T08:00:00Z,2026-10-01T09:30:00Z,S-003",
    "CBC,2026-10-01T08:00:00Z,2026-10-01T12:00:00Z,S-004",
    "CRP,2026-10-01T10:00:00+02:00,2026-10-01T09:20:00Z,S-005"
  ].join("\n");

  function parseCSV(input) {
    if (input.length > MAX_CHARS) throw new Error("CSV exceeds 2,000,000 characters.");
    const text = input.replace(/^\uFEFF/, "");
    const rows = [];
    let row = [], cell = "", quoted = false, closed = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (ch === '"') { quoted = false; closed = true; }
        else { cell += ch; }
      } else if (ch === '"' && cell === "" && !closed) {
        quoted = true;
      } else if (ch === "," || ch === "\n" || ch === "\r") {
        row.push(cell); cell = ""; closed = false;
        if (ch !== ",") {
          if (row.some(v => v !== "")) rows.push(row);
          row = [];
          if (ch === "\r" && text[i + 1] === "\n") i++;
        }
      } else if (ch === '"' || closed) {
        throw new Error("Malformed CSV quoting.");
      } else {
        cell += ch;
      }
    }
    if (quoted) throw new Error("Unterminated quoted CSV field.");
    if (cell !== "" || row.length) {
      row.push(cell);
      if (row.some(v => v !== "")) rows.push(row);
    }
    if (!rows.length) throw new Error("CSV is missing a header.");
    const columns = rows.shift().map(x => x.trim());
    if (columns.some(x => !x) || new Set(columns).size !== columns.length) {
      throw new Error("CSV has duplicate or empty column names.");
    }
    const missing = REQUIRED.filter(x => !columns.includes(x));
    if (missing.length) throw new Error("Missing required columns: " + missing.join(", "));
    if (!rows.length) throw new Error("CSV contains no data rows.");
    if (rows.length > MAX_RECORDS) throw new Error("CSV exceeds 20,000 records.");
    return { columns, records: rows.map((values, i) => {
      if (values.length !== columns.length) {
        throw new Error("Row " + (i + 2) + ": column count does not match header.");
      }
      return Object.fromEntries(columns.map((key, j) => [key, values[j]]));
    }) };
  }

  function parseTime(value, row, column) {
    const val = (value || "").trim();
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})$/.exec(val);
    if (!match) throw new Error("Row " + row + ": " + column + " must be ISO 8601 with seconds and timezone (Z or ±HH:MM).");
    const [, year, month, day, hour, minute, second, , zone] = match;
    const maxDay = new Date(Date.UTC(+year, +month, 0)).getUTCDate();
    if (+month < 1 || +month > 12 || +day < 1 || +day > maxDay ||
        +hour > 23 || +minute > 59 || +second > 59) {
      throw new Error("Row " + row + ": invalid " + column + " timestamp.");
    }
    if (zone !== "Z") {
      const zh = +zone.slice(1, 3), zm = +zone.slice(4, 6);
      if (zh > 23 || zm > 59) throw new Error("Row " + row + ": invalid timezone offset.");
    }
    const time = Date.parse(val);
    if (!Number.isFinite(time)) throw new Error("Row " + row + ": invalid " + column + " timestamp.");
    return time;
  }

  function quantile(values, p) {
    const sorted = [...values].sort((a, b) => a - b);
    const pos = (sorted.length - 1) * p;
    const low = Math.floor(pos), high = Math.ceil(pos);
    return sorted[low] + (sorted[high] - sorted[low]) * (pos - low);
  }

  function round(value, digits = 3) {
    return Math.round((value + Number.EPSILON) * (10 ** digits)) / (10 ** digits);
  }

  function summarize(group, threshold) {
    const values = group.map(x => x.tat_minutes);
    const breached = values.filter(x => x > threshold).length;
    return {
      count: group.length,
      mean_minutes: round(values.reduce((a, b) => a + b, 0) / values.length),
      p50_minutes: round(quantile(values, .50)),
      p90_minutes: round(quantile(values, .90)),
      p95_minutes: round(quantile(values, .95)),
      max_minutes: round(Math.max(...values)),
      breach_count: breached,
      breach_rate_pct: round(100 * breached / values.length),
      outlier_count: group.filter(x => x.outlier).length
    };
  }

  function analyzeCSV(csvText, thresholdMinutes = 60) {
    const threshold = Number(thresholdMinutes);
    if (!Number.isFinite(threshold) || threshold <= 0) {
      throw new Error("Threshold must be positive and finite, in minutes.");
    }
    const { columns, records: raw } = parseCSV(csvText);
    const records = [];
    const groups = new Map();
    raw.forEach((row, i) => {
      const line = i + 2, test = row.test.trim();
      if (!test) throw new Error("Row " + line + ": test cannot be empty.");
      const start = parseTime(row.received_at, line, "received_at");
      const end = parseTime(row.reported_at, line, "reported_at");
      if (end < start) throw new Error("Row " + line + ": reported_at precedes received_at.");
      const tat = round((end - start) / 60000, 6);
      const record = { ...row, test, tat_minutes: tat, breached: tat > threshold, outlier: false };
      records.push(record);
      if (!groups.has(test)) groups.set(test, []);
      groups.get(test).push(record);
    });
    for (const group of groups.values()) {
      if (group.length < 4) continue;
      const vals = group.map(x => x.tat_minutes);
      const q1 = quantile(vals, .25), q3 = quantile(vals, .75);
      const limit = q3 + 1.5 * (q3 - q1);
      group.forEach(record => { record.outlier = record.tat_minutes > limit; });
    }
    const by_test = {};
    for (const name of [...groups.keys()].sort()) by_test[name] = summarize(groups.get(name), threshold);
    return { threshold_minutes: threshold, overall: summarize(records, threshold),
             by_test, records, input_columns: columns };
  }

  function csvEscape(value, untrusted = false) {
    let cell = String(value === undefined || value === null ? "" : value);
    if (untrusted && /^[\s]*[=+\-@]/.test(cell)) cell = "'" + cell;
    return '"' + cell.replace(/"/g, '""') + '"';
  }

  function annotatedCSV(result) {
    const fields = result.input_columns.filter(x => !["tat_minutes", "breached", "outlier"].includes(x))
      .concat(["tat_minutes", "breached", "outlier"]);
    return [fields.map(x => csvEscape(x)).join(",")].concat(
      result.records.map(row => fields.map(name => csvEscape(row[name], result.input_columns.includes(name))).join(","))
    ).join("\r\n") + "\r\n";
  }

  const TAT = { parseCSV, analyzeCSV, annotatedCSV, EXAMPLE };
  if (typeof module !== "undefined" && module.exports) module.exports = TAT;
  if (root) root.TAT = TAT;

  if (typeof document === "undefined") return;
  document.addEventListener("DOMContentLoaded", () => {
    const byId = id => document.getElementById(id);
    const fileInput = byId("file");
    const thresholdInput = byId("threshold");
    const message = byId("message");
    const table = byId("by-test");
    const resultArea = byId("results");
    let result = null;

    function status(text, error = false) {
      message.textContent = text;
      message.className = error ? "status error" : "status";
    }
    function metric(id, value) { byId(id).textContent = String(value); }
    function addCell(row, value, tag = "td") {
      const cell = document.createElement(tag);
      cell.textContent = String(value);
      row.appendChild(cell);
    }
    function render(data) {
      result = data;
      const o = data.overall;
      metric("n", o.count);
      metric("p90", o.p90_minutes.toFixed(1) + " min");
      metric("breach", o.breach_rate_pct.toFixed(1) + "%");
      metric("outlier", o.outlier_count);
      table.replaceChildren();
      for (const [name, v] of Object.entries(data.by_test)) {
        const tr = document.createElement("tr");
        [name, v.count, v.mean_minutes, v.p50_minutes, v.p90_minutes,
          v.p95_minutes, v.breach_count, v.breach_rate_pct + "%", v.outlier_count]
          .forEach((value, i) => addCell(tr, value, i === 0 ? "th" : "td"));
        table.appendChild(tr);
      }
      resultArea.hidden = false;
      byId("placeholder").hidden = true;
      status("Analyzed " + o.count + " records locally. Target: " + data.threshold_minutes + " minutes.");
    }

    async function run() {
      result = null;
      resultArea.hidden = true;
      byId("placeholder").hidden = false;
      const threshold = Number(thresholdInput.value);
      try {
        if (!Number.isFinite(threshold) || threshold <= 0 || thresholdInput.value.trim() === "") {
          throw new Error("Enter a positive TAT target in minutes.");
        }
        if (!fileInput.files || fileInput.files.length !== 1) throw new Error("Select a CSV file or choose Load example.");
        const file = fileInput.files[0];
        if (file.size > MAX_CHARS * 4) throw new Error("Selected file exceeds the size limit.");
        render(analyzeCSV(await file.text(), threshold));
      } catch (err) { status(err.message || String(err), true); }
    }

    function download(name, content, type) {
      const url = URL.createObjectURL(new Blob([content], { type }));
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    }
    byId("form").addEventListener("submit", event => { event.preventDefault(); run(); });
    byId("example").addEventListener("click", () => {
      try {
        render(analyzeCSV(EXAMPLE, Number(thresholdInput.value)));
      } catch (err) { status(err.message || String(err), true); }
    });
    byId("csv-export").addEventListener("click", () => {
      if (result) download("tat-annotated.csv", annotatedCSV(result), "text/csv;charset=utf-8");
    });
    byId("json-export").addEventListener("click", () => {
      if (result) {
        const { threshold_minutes, overall, by_test } = result;
        download("tat-summary.json", JSON.stringify({ threshold_minutes, overall, by_test }, null, 2), "application/json");
      }
    });
  });
})(typeof window === "undefined" ? null : window);
