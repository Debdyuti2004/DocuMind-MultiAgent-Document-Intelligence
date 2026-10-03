import { api, escapeHtml, formatDate, displayName } from "./core.js";

let current = null;
let payload = { summary: null, sources: null, analysis: null };
let activeTab = "overview";

const renderList = values => values?.length
  ? `<ul class="fact-list">${values.map(value => `<li>${escapeHtml(value)}</li>`).join("")}</ul>`
  : `<p class="muted" style="font-size:11px">Not available for this document.</p>`;

function renderTables(tables = []) {
  if (!tables.length) return `<p class="muted">No extracted tables are available for this document.</p>`;
  return tables.map((table, index) => {
    const headers = table.headers || [];
    const rows = table.rows || [];
    return `<div class="table-card"><h3>${escapeHtml(table.title || `Table ${index + 1}`)} · page ${escapeHtml(table.page ?? "—")}</h3><table><thead><tr>${headers.map(value => `<th>${escapeHtml(value)}</th>`).join("")}</tr></thead><tbody>${rows.map(row => `<tr>${row.map(value => `<td>${escapeHtml(value)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
  }).join("");
}

function renderChunkList(chunks = [], heading = "Source text") {
  if (!chunks.length) return `<div class="empty"><b>No extracted text available.</b>The document may be image-only or unsupported.</div>`;
  return `<h2>${heading}</h2>${chunks.map((chunk, index) => `<details class="chunk-card" ${index === 0 ? "open" : ""}><summary><b>${escapeHtml(chunk.filename || current.filename)}</b> · page ${escapeHtml(chunk.page ?? "—")} · ${escapeHtml(chunk.section || "Content")}</summary><p>${escapeHtml(chunk.text || "")}</p></details>`).join("")}`;
}

function renderOverview() {
  const summary = payload.summary;
  if (!summary) return `<div class="empty"><b>Summary unavailable.</b>Check that text extraction completed for this document.</div>`;
  const entities = Object.entries(summary.key_entities || {}).filter(([, values]) => values?.length);
  return `<div class="detail-section"><h2>Executive summary</h2><p class="detail-summary">${escapeHtml(summary.executive_summary || "Not available for this document.")}</p><h2>Key facts</h2>${renderList(summary.key_facts)}<h2>Key findings</h2>${renderList(summary.important_findings)}<h2>Topics</h2>${summary.key_topics?.length ? `<div class="entity-list">${summary.key_topics.map(topic => `<span class="entity-chip">${escapeHtml(topic)}</span>`).join("")}</div>` : `<p class="muted">Not available for this document.</p>`}<h2>Explicit risk-related passages</h2>${renderList(summary.potential_risks)}</div>`;
}

function renderAnalysis() {
  const analysis = payload.analysis;
  if (!analysis) return `<div class="empty"><b>Analysis unavailable.</b>The API could not retrieve extracted tables.</div>`;
  const metrics = Object.entries(analysis.metrics || {});
  return `<div class="detail-section"><h2>Extracted values</h2>${metrics.length ? `<div class="metric-grid">${metrics.map(([label, value]) => `<div class="metric"><b>${escapeHtml(label)}</b><div class="metric-values"><span>${escapeHtml(value)}</span></div><small class="muted">Extracted from indexed text</small></div>`).join("")}</div>` : `<p class="muted">No supported financial values were extracted.</p>`}<h2>Extracted tables</h2>${renderTables(analysis.tables || [])}</div>`;
}

function renderMetadata() {
  const meta = current;
  const rows = [
    ["Document ID", meta.document_id], ["Filename", meta.filename], ["Title", meta.title],
    ["File type", meta.file_type], ["Size", `${(meta.file_size_bytes / 1024).toFixed(1)} KiB`],
    ["Document type", meta.document_type], ["Domain", meta.domain],
    ["Heuristic classification score", `${Math.round((meta.classification_confidence || 0) * 100)}%`],
    ["Pages", meta.num_pages], ["Chunks", meta.num_chunks], ["Tables", meta.num_tables], ["Added", formatDate(meta.created_at)],
  ];
  return `<div class="detail-section"><h2>Document metadata</h2><div class="metadata-grid">${rows.map(([label, value]) => `<div><small>${escapeHtml(label)}</small><b>${escapeHtml(value ?? "Not available")}</b></div>`).join("")}</div></div>`;
}

function renderSources() {
  const chunks = payload.sources?.chunks || [];
  return `<div class="detail-section"><h2>Indexed source chunks</h2><p class="muted" style="font-size:11px">Page and section values come from parser metadata. Expand a chunk to inspect the indexed evidence.</p>${renderChunkList(chunks)}</div>`;
}

function renderActiveTab() {
  const body = document.querySelector("#detailBody");
  if (!body) return;
  const content = {
    overview: renderOverview,
    content: () => `<div class="detail-section">${renderChunkList(payload.sources?.chunks || [], "Extracted document content")}</div>`,
    analysis: renderAnalysis,
    sources: renderSources,
    metadata: renderMetadata,
  }[activeTab] || renderOverview;
  body.innerHTML = content();
  document.querySelectorAll("[data-detail-tab]").forEach(button => button.classList.toggle("active", button.dataset.detailTab === activeTab));
}

export async function openDocument(meta) {
  current = meta;
  activeTab = "overview";
  document.querySelector("#detailTitle").textContent = displayName(meta);
  document.querySelector("#detailSubtitle").textContent = `${meta.filename} · ${meta.domain || "Domain unavailable"}`;
  document.querySelector("#detailType").textContent = `${meta.document_type || "General"} · ${meta.file_type || "file"}`;
  document.querySelector("#detailStats").innerHTML = [
    ["Pages", meta.num_pages ?? "—"], ["Indexed chunks", meta.num_chunks ?? "—"],
    ["Tables", meta.num_tables ?? "—"], ["Added", formatDate(meta.created_at)],
  ].map(([label, value]) => `<article class="card stat"><div class="stat-top">${escapeHtml(label)}</div><div class="stat-number">${escapeHtml(value)}</div></article>`).join("");
  document.querySelector("#classificationBody").innerHTML = `<div class="setting-row"><div><b>${escapeHtml(meta.document_type || "Not available")}</b><small>Document type</small></div></div><div class="setting-row"><div><b>${escapeHtml(meta.domain || "Not available")}</b><small>Domain</small></div></div><div class="setting-row"><div><b>${Math.round((meta.classification_confidence || 0) * 100)}%</b><small>Heuristic score · not a calibrated probability</small></div></div>`;
  document.querySelector("#detailBody").innerHTML = `<div class="empty">Loading document intelligence…</div>`;
  document.querySelector("#entityBody").innerHTML = `<span class="muted" style="font-size:11px">Loading…</span>`;
  document.querySelector("#detailSuggestions").innerHTML = "";

  const id = encodeURIComponent(meta.document_id);
  const [summaryResult, sourceResult, analysisResult] = await Promise.allSettled([
    api(`/documents/${id}/summary`), api(`/documents/${id}/sources`), api(`/documents/${id}/analysis`),
  ]);
  payload = {
    summary: summaryResult.status === "fulfilled" ? summaryResult.value : null,
    sources: sourceResult.status === "fulfilled" ? sourceResult.value : null,
    analysis: analysisResult.status === "fulfilled" ? analysisResult.value : null,
  };
  renderActiveTab();

  const entities = Object.entries(payload.summary?.key_entities || {}).flatMap(([group, values]) => (values || []).map(value => [group, value]));
  document.querySelector("#entityBody").innerHTML = entities.length
    ? entities.map(([group, value]) => `<span class="entity-chip" title="${escapeHtml(group)}">${escapeHtml(value)}</span>`).join("")
    : `<span class="muted" style="font-size:11px">No entities extracted.</span>`;
  const questions = payload.summary?.suggested_questions || [];
  document.querySelector("#detailSuggestions").innerHTML = questions.length
    ? questions.map(question => `<button data-detail-question="${escapeHtml(question)}">${escapeHtml(question)}</button>`).join("")
    : `<span class="muted" style="font-size:11px">No suggested questions available.</span>`;
  return { meta: current, summary: payload.summary, sources: payload.sources, analysis: payload.analysis };
}

export function activeDocument() { return current; }
export function setDetailTab(tab) { activeTab = tab; renderActiveTab(); }
