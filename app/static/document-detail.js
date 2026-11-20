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
  return `<h2>${heading}</h2>${chunks.map((chunk, index) => {
    const langBadge = chunk.language && chunk.language !== "en" ? `<span class="lang-badge lang-${escapeHtml(chunk.language)}">${escapeHtml(chunk.language)}</span> ` : "";
    return `<details class="chunk-card" ${index === 0 ? "open" : ""}><summary>${langBadge}<b>${escapeHtml(chunk.filename || current.filename)}</b> · page ${escapeHtml(chunk.page ?? "—")} · ${escapeHtml(chunk.section || "Content")}</summary><p>${escapeHtml(chunk.text || "")}</p></details>`;
  }).join("")}`;
}

function renderSideBySide() {
  const chunks = payload.sources?.chunks || [];
  if (!chunks.length) return `<div class="empty"><b>No text chunks available.</b></div>`;
  const docLang = current?.language || "Source Language";
  return `<div class="detail-section"><h2>Side-by-side multilingual view</h2><p class="muted" style="font-size:11px">Original document text alongside aligned English translation representation.</p><div class="side-by-side-grid">${chunks.map((chunk, idx) => `
    <div class="side-by-side-col">
      <h3>Original (${escapeHtml(chunk.language || current?.language_code || docLang)}) <small class="muted">page ${escapeHtml(chunk.page || 1)}</small></h3>
      <p style="font-size:11px;line-height:1.6;white-space:pre-wrap">${escapeHtml(chunk.text || "")}</p>
    </div>
    <div class="side-by-side-col">
      <h3>English Representation <small class="muted">chunk ${idx + 1}</small></h3>
      <p style="font-size:11px;line-height:1.6;white-space:pre-wrap">${escapeHtml(chunk.translated_text || chunk.text || "")}</p>
    </div>
  `).join("")}</div></div>`;
}

function renderOverview() {
  const summary = payload.summary;
  if (!summary) return `<div class="empty"><b>Summary unavailable.</b>Check that text extraction completed for this document.</div>`;
  const meta = current || {};
  const isTranslated = summary.is_translated || (meta.language_code && meta.language_code !== "en");
  const translationBanner = isTranslated ? `
    <div class="result-meta" style="margin-bottom:12px;background:#f0efff;padding:8px 12px;border-radius:9px;border:1px solid #e1deff">
      <span class="lang-badge lang-${escapeHtml(meta.language_code || 'en')}">Original: ${escapeHtml(meta.language || 'Non-English')}</span>
      <span class="badge" style="background:#fff">English Output (Default)</span>
      <span class="muted" style="font-size:10px">Preserving names, metrics, and citations</span>
    </div>
  ` : "";
  const origSummarySnippet = summary.original_language_summary ? `
    <details style="margin:10px 0 16px;font-size:11px;background:var(--wash);padding:10px;border-radius:8px;border:1px solid var(--line)">
      <summary style="cursor:pointer;color:var(--purple);font-weight:700">View original ${escapeHtml(meta.language || "")} executive summary</summary>
      <p style="margin-top:8px;line-height:1.6;color:var(--ink)">${escapeHtml(summary.original_language_summary)}</p>
    </details>
  ` : "";

  return `<div class="detail-section">${translationBanner}<h2>Executive summary</h2><p class="detail-summary">${escapeHtml(summary.executive_summary || "Not available for this document.")}</p>${origSummarySnippet}<h2>Key facts</h2>${renderList(summary.key_facts)}<h2>Key findings</h2>${renderList(summary.important_findings)}<h2>Topics</h2>${summary.key_topics?.length ? `<div class="entity-list">${summary.key_topics.map(topic => `<span class="entity-chip">${escapeHtml(topic)}</span>`).join("")}</div>` : `<p class="muted">Not available for this document.</p>`}<h2>Explicit risk-related passages</h2>${renderList(summary.potential_risks)}</div>`;
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
    ["Detected Language", `${meta.language || "English"} (${meta.language_code || "en"})`],
    ["Language Confidence", `${Math.round((meta.language_confidence || 1.0) * 100)}%`],
    ["Mixed Language", meta.is_mixed_language ? "Yes" : "No"],
    ["Additional Languages", (meta.additional_languages || []).join(", ") || "None"],
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
    "side-by-side": renderSideBySide,
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
    ["Language", meta.language || "English"],
    ["Pages", meta.num_pages ?? "—"],
    ["Indexed chunks", meta.num_chunks ?? "—"],
    ["Tables", meta.num_tables ?? "—"],
  ].map(([label, value]) => `<article class="card stat"><div class="stat-top">${escapeHtml(label)}</div><div class="stat-number small-number">${escapeHtml(value)}</div></article>`).join("");

  const langCode = meta.language_code || "en";
  const langName = meta.language || "English";
  const conf = Math.round((meta.language_confidence || 1.0) * 100);
  const warn = meta.language_warning ? `<p class="muted" style="color:#d35400;font-size:10px;margin-top:6px">⚠️ ${escapeHtml(meta.language_warning)}</p>` : "";
  const mixed = meta.is_mixed_language ? `<span class="badge" style="background:#fff3cd;color:#856404">Mixed language</span>` : "";
  const addLangs = (meta.additional_languages || []).length ? `<div style="font-size:10px;color:var(--muted);margin-top:4px">Additional: ${escapeHtml(meta.additional_languages.join(", "))}</div>` : "";
  const langBody = document.querySelector("#languageDetailBody");
  if (langBody) {
    langBody.innerHTML = `
      <div class="setting-row">
        <div>
          <b><span class="lang-badge lang-${escapeHtml(langCode)}">${escapeHtml(langName)}</span> ${mixed}</b>
          <small>Detection confidence: ${conf}%</small>
          ${addLangs}
          ${warn}
        </div>
      </div>
    `;
  }

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
