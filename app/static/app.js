import { api, escapeHtml, notify, formatDate, displayName, sessionId, queryHistory, saveQuery, clearQueryHistory } from "./core.js";
import { openDocument, activeDocument, setDetailTab } from "./document-detail.js";

const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
let documents = [];
let runtimeConfig = null;
let selectedQueryDocs = new Set();
let gridMode = false;
let currentConversation = [];

function setView(view) {
  $$(".view").forEach(section => section.classList.toggle("active", section.id === view));
  $$(".nav button").forEach(button => button.classList.toggle("active", button.dataset.view === view));
  const labels = { overview: "Overview", documents: "Documents", ask: "Ask DocuMind", compare: "Compare", analytics: "Analytics", agents: "Agent activity", history: "History", settings: "Settings", "document-detail": "Document details" };
  $("#crumb").textContent = labels[view] || "Overview";
  if (view === "analytics") renderAnalytics();
  if (view === "agents") renderAgentRuns();
  if (view === "history") renderHistory();
  if (view === "settings") renderSettings();
  if (view === "ask") { renderScopeOptions(); renderConversation(); }
}

$(".nav").addEventListener("click", event => {
  const button = event.target.closest("[data-view]");
  if (button) setView(button.dataset.view);
});
document.addEventListener("click", event => {
  const go = event.target.closest("[data-go]");
  if (go) setView(go.dataset.go);
});

function setApiStatus(healthy, detail = "") {
  $("#sideDot").style.background = healthy ? "#42c4a1" : "#e39b46";
  $("#topDot").style.background = healthy ? "#42c4a1" : "#e39b46";
  $("#sideHealth").textContent = healthy ? "DocuMind is online" : "API unavailable";
  $("#sideHealthDetail").textContent = detail || (healthy ? "API and index are responding." : "Start the DocuMind server and refresh.");
  $("#apiText").textContent = healthy ? "API connected" : "API offline";
}

async function loadHealthAndConfig() {
  try {
    const [health, config] = await Promise.all([api("/health"), api("/config")]);
    runtimeConfig = config;
    setApiStatus(true, `Extractive QA · ${Number(health.vector_store_chunks || 0).toLocaleString()} indexed chunks`);
    $("#statChunks").textContent = Number(health.vector_store_chunks || 0).toLocaleString();
    $("#researchToggle").disabled = !config.external_research_available;
    $("#researchToggle").title = config.external_research_available ? "Allow external research for this query" : "External search is not configured";
  } catch (error) {
    setApiStatus(false);
    notify(error.message, true);
  }
}

function iconForFile(filename = "") {
  const extension = (filename.split(".").pop() || "FILE").slice(0, 4).toUpperCase();
  const doc = /doc|txt|ppt|xls|csv/i.test(extension);
  return `<span class="file-ico ${doc ? "doc" : ""}">${escapeHtml(extension)}</span>`;
}

function emptyRow(columns, message, detail = "") {
  return `<tr><td colspan="${columns}"><div class="empty"><b>${escapeHtml(message)}</b>${escapeHtml(detail)}</div></td></tr>`;
}

function groupCount(property) {
  return documents.reduce((counts, document) => {
    const key = document[property] || "Unclassified";
    counts[key] = (counts[key] || 0) + 1;
    return counts;
  }, {});
}

function renderBars(selector, counts) {
  const target = $(selector);
  const entries = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...entries.map(([, count]) => count));
  target.innerHTML = entries.length ? entries.map(([label, count]) => `<div class="bar-row"><span title="${escapeHtml(label)}">${escapeHtml(label)}</span><div class="bar-track"><div class="bar-fill" style="width:${Math.max(2, count / max * 100)}%"></div></div><b>${count}</b></div>`).join("") : `<p class="muted">No indexed documents.</p>`;
}

function renderScopeOptions() {
  const menu = $("#scopeMenu");
  if (!menu) return;
  menu.innerHTML = documents.length ? documents.map(document => `<label><input type="checkbox" data-scope-id="${escapeHtml(document.document_id)}" ${selectedQueryDocs.has(document.document_id) ? "checked" : ""}><span>${escapeHtml(displayName(document))}</span></label>`).join("") : `<span class="muted" style="font-size:11px">No documents indexed yet.</span>`;
  const count = selectedQueryDocs.size;
  $("#scopeButton").textContent = count ? `${count} document${count === 1 ? "" : "s"} selected⌄` : "All documents⌄";
}

function sortDocuments(items) {
  const sort = $("#sortDocs")?.value || "date-desc";
  return items.sort((a, b) => {
    if (sort === "name-asc") return displayName(a).localeCompare(displayName(b));
    if (sort === "name-desc") return displayName(b).localeCompare(displayName(a));
    const direction = sort === "date-asc" ? 1 : -1;
    return direction * (new Date(a.created_at || 0) - new Date(b.created_at || 0));
  });
}

function documentActions(document) {
  const id = escapeHtml(document.document_id);
  return `<button class="link-button" data-open="${id}">Open</button><button class="link-button danger-link" data-delete="${id}" aria-label="Delete ${escapeHtml(displayName(document))}">Delete</button>`;
}

function renderDocumentGrid(items) {
  const grid = $("#docGrid");
  grid.hidden = !gridMode;
  $("#docTableWrap").hidden = gridMode;
  $("#viewToggle").textContent = gridMode ? "☰ List" : "▦ Grid";
  grid.innerHTML = items.length ? items.map(document => `<article class="document-card"><button class="document-card-title" data-open="${escapeHtml(document.document_id)}">${iconForFile(document.filename)}<span><b>${escapeHtml(displayName(document))}</b><small>${escapeHtml(document.document_type || "General")} · ${escapeHtml(document.domain || "Domain unavailable")}</small></span></button><div class="document-card-stats"><span>${document.num_pages ?? "—"} pages</span><span>${document.num_chunks ?? "—"} chunks</span><span>${document.num_tables ?? "—"} tables</span></div><div class="document-card-footer"><small>${formatDate(document.created_at)}</small><div>${documentActions(document)}</div></div></article>`).join("") : `<div class="empty"><b>No matching documents.</b>Try changing the search or filters.</div>`;
}

function renderRows() {
  const query = $("#searchDocs").value.trim().toLowerCase();
  const type = $("#filterType").value;
  const domain = $("#filterDomain").value;
  const matching = sortDocuments(documents.filter(document => {
    const haystack = [document.filename, document.title, document.document_type, document.domain].join(" ").toLowerCase();
    return (!type || document.document_type === type) && (!domain || document.domain === domain) && (!query || haystack.includes(query));
  }));
  $("#docCount").textContent = `(${matching.length})`;
  $("#docRows").innerHTML = matching.length ? matching.map(document => `<tr><td><div class="file-name">${iconForFile(document.filename)}<button class="document-name-button" data-open="${escapeHtml(document.document_id)}">${escapeHtml(displayName(document))}</button></div></td><td>${escapeHtml(document.document_type || "General")}</td><td>${escapeHtml(document.domain || "—")}</td><td>${document.num_pages ?? "—"}</td><td>${document.num_chunks ?? "—"}</td><td>${formatDate(document.created_at)}</td><td><div class="table-actions">${documentActions(document)}</div></td></tr>`).join("") : emptyRow(7, "No matching documents.", "Try changing the search or filters.");
  renderDocumentGrid(matching);
  $("#recentRows").innerHTML = documents.length ? documents.slice(0, 5).map(document => `<tr><td><div class="file-name">${iconForFile(document.filename)}<button class="document-name-button" data-open="${escapeHtml(document.document_id)}">${escapeHtml(displayName(document))}</button></div></td><td>${escapeHtml(document.document_type || "General")}</td><td>${document.num_pages ?? "—"}</td><td>${formatDate(document.created_at)}</td><td><span class="badge">Indexed</span></td></tr>`).join("") : emptyRow(5, "Your library is ready.", "Upload a document to get started.");
}

function renderDashboard() {
  const history = queryHistory();
  $("#statDocs").textContent = documents.length.toLocaleString();
  $("#statQueries").textContent = history.length.toLocaleString();
  $("#statTypes").textContent = Object.keys(groupCount("document_type")).length.toLocaleString();
  renderBars("#overviewDomainBars", groupCount("domain"));
  const latest = history.slice(0, 3);
  $("#recentActivity").innerHTML = latest.length ? latest.map(item => `<div class="history-item"><div><b>${escapeHtml(item.query)}</b><p>${escapeHtml((item.answer || item.error || "").slice(0, 180))}</p><span class="history-meta">${formatDate(item.created_at)} · ${escapeHtml(item.intent || "Query")}</span></div><button class="button outline" data-reopen-query="${escapeHtml(item.id)}">Open</button></div>`).join("") : `<div class="empty"><b>No recent activity yet.</b>Completed questions will appear here.</div>`;
}

function fillLibraryFilters() {
  const types = [...new Set(documents.map(document => document.document_type).filter(Boolean))].sort();
  const domains = [...new Set(documents.map(document => document.domain).filter(Boolean))].sort();
  const previousType = $("#filterType").value;
  const previousDomain = $("#filterDomain").value;
  $("#filterType").innerHTML = `<option value="">All categories</option>${types.map(type => `<option value="${escapeHtml(type)}">${escapeHtml(type)}</option>`).join("")}`;
  $("#filterDomain").innerHTML = `<option value="">All domains</option>${domains.map(domain => `<option value="${escapeHtml(domain)}">${escapeHtml(domain)}</option>`).join("")}`;
  $("#filterType").value = previousType;
  $("#filterDomain").value = previousDomain;
  renderScopeOptions();
  fillCompareOptions();
}

function fillCompareOptions() {
  for (const [selector, placeholder] of [["#compareA", "Select first document…"], ["#compareB", "Select second document…"]]) {
    const select = $(selector);
    const previous = select.value;
    select.innerHTML = `<option value="">${placeholder}</option>${documents.map(document => {
      const suffix = `${formatDate(document.created_at)} · ${document.document_id.slice(-4)}`;
      return `<option value="${escapeHtml(document.document_id)}">${escapeHtml(displayName(document))} · ${escapeHtml(suffix)}</option>`;
    }).join("")}`;
    if (documents.some(document => document.document_id === previous)) select.value = previous;
  }
}

async function refreshDocuments() {
  try {
    const list = await api("/documents");
    documents = list.sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0));
    fillLibraryFilters();
    renderRows();
    renderDashboard();
  } catch (error) {
    $("#docRows").innerHTML = emptyRow(7, "Could not load documents.", error.message);
    $("#recentRows").innerHTML = emptyRow(5, "Could not load documents.", error.message);
    notify(error.message, true);
  }
}

function renderAnalytics() {
  const pages = documents.reduce((sum, item) => sum + (item.num_pages || 0), 0);
  const chunks = documents.reduce((sum, item) => sum + (item.num_chunks || 0), 0);
  const tables = documents.reduce((sum, item) => sum + (item.num_tables || 0), 0);
  const history = queryHistory();
  $("#analyticsStats").innerHTML = [["Documents", documents.length], ["Pages", pages], ["Indexed chunks", chunks], ["Extracted tables", tables]].map(([label, value]) => `<article class="card stat"><div class="stat-top">${label}</div><div class="stat-number">${Number(value).toLocaleString()}</div><div class="stat-foot">${label === "Documents" ? "Current registry count" : "Sum from current metadata"}</div></article>`).join("");
  renderBars("#typeBars", groupCount("document_type"));
  renderBars("#domainBars", groupCount("domain"));
  $("#analyticsRows").innerHTML = documents.length ? documents.map(document => `<tr><td>${escapeHtml(displayName(document))}</td><td>${escapeHtml(document.domain || "—")}</td><td>${document.num_pages ?? "—"}</td><td>${document.num_chunks ?? "—"}</td><td>${document.num_tables ?? "—"}</td></tr>`).join("") : emptyRow(5, "No indexed documents.");
  $("#statQueries").textContent = history.length.toLocaleString();
}

function renderHistory() {
  const items = queryHistory();
  $("#historyRows").innerHTML = items.length ? items.map(item => `<article class="history-item"><div><b>${escapeHtml(item.query)}</b><p>${escapeHtml((item.answer || item.error || "No answer text was returned.").slice(0, 260))}</p><span class="history-meta">${formatDate(item.created_at)} · ${escapeHtml(item.intent || "Query")} · ${item.document_ids?.length || 0} selected document(s)</span></div><button class="button outline" data-reopen-query="${escapeHtml(item.id)}">Reopen</button></article>`).join("") : `<div class="empty"><b>No saved queries yet.</b>Ask a document question to create local history.</div>`;
}

function renderAgentRuns() {
  const runs = queryHistory().filter(item => Array.isArray(item.agent_logs) && item.agent_logs.length);
  const count = runs.reduce((sum, run) => sum + run.agent_logs.length, 0);
  const unique = new Set(runs.flatMap(run => run.agent_logs.map(log => log.agent_name))).size;
  $("#agentSummary").innerHTML = [["Recorded queries", runs.length], ["Logged workflow steps", count], ["Agent names observed", unique], ["Activity source", "Actual API logs"]].map(([label, value]) => `<article class="card stat"><div class="stat-top">${escapeHtml(label)}</div><div class="stat-number ${typeof value === "string" ? "small-number" : ""}">${escapeHtml(value)}</div><div class="stat-foot">From completed responses in this browser</div></article>`).join("");
  $("#agentRuns").innerHTML = runs.length ? runs.map(run => `<article class="card agent-run"><div class="agent-run-head"><div><b>${escapeHtml(run.query)}</b><div class="history-meta">${formatDate(run.created_at)} · ${escapeHtml(run.intent || "Query")} · ${Number(run.execution_time_seconds || 0).toFixed(2)}s total</div></div><span class="badge">${run.agent_logs.length} logged step(s)</span></div><div class="agent-trace">${run.agent_logs.map(log => `<div class="agent-step ${escapeHtml(log.status || "completed")}"><strong>${escapeHtml(log.agent_name)}</strong><small>${escapeHtml(log.action)}${log.execution_time_ms != null ? ` · ${Number(log.execution_time_ms).toFixed(1)} ms` : ""}</small><small>${escapeHtml(log.detail)}</small></div>`).join("")}</div></article>`).join("") : `<div class="card panel empty"><b>No logged agent runs in this browser.</b>Run a query to inspect the actual workflow logs returned by the orchestrator.</div>`;
}

async function renderSettings() {
  if (!runtimeConfig) {
    try { runtimeConfig = await api("/config"); }
    catch (error) { $("#runtimeSettings").innerHTML = `<div class="empty">${escapeHtml(error.message)}</div>`; return; }
  }
  const rows = [
    ["Configured provider (not used by current query flow)", runtimeConfig.llm_provider], ["Configured model", runtimeConfig.llm_model],
    ["Embedding model", runtimeConfig.embedding_model], ["Retrieved chunks (top K)", runtimeConfig.top_k],
    ["Chunk size", runtimeConfig.chunk_size], ["Chunk overlap", runtimeConfig.chunk_overlap],
    ["Similarity threshold", runtimeConfig.similarity_threshold],
    ["Upload limit", `${(runtimeConfig.max_upload_bytes / (1024 * 1024)).toFixed(0)} MiB`],
    ["Supported files", runtimeConfig.supported_extensions.join(", ")],
  ];
  $("#runtimeSettings").innerHTML = rows.map(([key, value]) => `<div class="setting-row"><div><b>${escapeHtml(key)}</b><small>${escapeHtml(value)}</small></div></div>`).join("");
  $("#capabilities").innerHTML = [["OCR", runtimeConfig.ocr_available ? "Available" : "Not configured"], ["External research", runtimeConfig.external_research_available ? "Available" : "Not configured"], ["Conversation memory", "In-memory, server process lifetime"], ["Query history", "Local to this browser"]].map(([key, value]) => `<div class="setting-row"><div><b>${escapeHtml(key)}</b><small>${escapeHtml(value)}</small></div></div>`).join("");
}

function renderSource(source) {
  return `<details class="source"><summary><b>${escapeHtml(source.document_name)}</b> · page ${escapeHtml(source.page)} · ${escapeHtml(source.section || "Content")}</summary><p>${escapeHtml(source.snippet || "Evidence snippet unavailable.")}</p></details>`;
}

function renderQueryResult(item) {
  const area = $("#answerArea");
  const answer = item.answer || item.error || "No answer text was returned.";
  const response = item.response || {};
  const sources = response.sources || [];
  const claims = response.verified_claims || [];
  const logs = item.agent_logs || [];
  area.innerHTML = `<article class="card result query-chat"><div class="user-question"><span class="avatar">You</span><div><small>Your question</small><b>${escapeHtml(item.query)}</b></div></div><div class="answer-wrap"><div class="answer-mark">D</div><div class="answer-content"><div class="result-meta"><span class="confidence">${escapeHtml(item.intent || "Document query")}</span>${item.confidence ? `<span class="muted">Evidence match rate · ${Math.round((item.confidence_score || 0) * 100)}%</span>` : ""}${item.execution_time_seconds != null ? `<span class="muted">${Number(item.execution_time_seconds).toFixed(2)}s</span>` : ""}</div><div class="answer">${escapeHtml(answer)}</div>${item.error ? "" : sources.length ? `<h3 class="mini-heading">Sources and evidence</h3><div class="source-list">${sources.map(renderSource).join("")}</div>` : `<p class="muted source-unavailable">Source evidence metadata is unavailable for this response.</p>`}${claims.length ? `<h3 class="mini-heading">Claim checks</h3><div class="source-list">${claims.map(claim => `<details class="source ${claim.supported ? "supported" : "unsupported"}"><summary><b>${claim.supported ? "Supported by exact evidence / calculation" : "Not supported"}</b> · ${escapeHtml(claim.claim)}</summary><p>${escapeHtml(claim.reasoning || "No verification explanation returned.")}</p>${claim.source_filenames?.length ? `<p>${escapeHtml(claim.source_filenames.join(", "))} · page(s) ${escapeHtml(claim.source_pages?.join(", ") || "—")}</p>` : ""}${claim.evidence_text ? `<blockquote>${escapeHtml(claim.evidence_text)}</blockquote>` : ""}</details>`).join("")}</div>` : ""}${logs.length ? `<details class="workflow-details"><summary>Workflow details · ${logs.length} logged steps</summary><div class="agent-trace">${logs.map(log => `<div class="agent-step ${escapeHtml(log.status || "completed")}"><strong>${escapeHtml(log.agent_name)}</strong><small>${escapeHtml(log.action)}${log.execution_time_ms != null ? ` · ${Number(log.execution_time_ms).toFixed(1)} ms` : ""}</small><small>${escapeHtml(log.detail)}</small></div>`).join("")}</div></details>` : ""}</div></div></article>`;
}

function renderConversation() {
  if (currentConversation.length) renderQueryResult(currentConversation.at(-1));
}

function reopenHistory(id) {
  const item = queryHistory().find(entry => entry.id === id);
  if (!item) return;
  currentConversation = [item];
  $("#queryInput").value = item.query;
  setView("ask");
  renderQueryResult(item);
}

document.addEventListener("click", async event => {
  const open = event.target.closest("[data-open]");
  const summary = event.target.closest("[data-summary]");
  const remove = event.target.closest("[data-delete]");
  const question = event.target.closest("[data-detail-question]");
  const reopen = event.target.closest("[data-reopen-query]");
  if (open) {
    const meta = documents.find(document => document.document_id === open.dataset.open);
    if (meta) {
      try { await openDocument(meta); setView("document-detail"); }
      catch (error) { notify(error.message, true); }
    }
  } else if (summary) {
    const meta = documents.find(document => document.document_id === summary.dataset.summary);
    if (meta) {
      try { await openDocument(meta); setDetailTab("overview"); setView("document-detail"); }
      catch (error) { notify(error.message, true); }
    }
  } else if (remove) {
    const meta = documents.find(document => document.document_id === remove.dataset.delete);
    if (!meta || !window.confirm(`Delete “${displayName(meta)}” from the DocuMind index? This removes its metadata, summary, and indexed chunks.`)) return;
    try {
      await api(`/documents/${encodeURIComponent(meta.document_id)}`, { method: "DELETE" });
      selectedQueryDocs.delete(meta.document_id);
      notify("Document removed from the index.");
      await refreshDocuments();
    } catch (error) { notify(error.message, true); }
  } else if (question) {
    selectedQueryDocs = new Set(activeDocument() ? [activeDocument().document_id] : []);
    renderScopeOptions();
    $("#queryInput").value = question.dataset.detailQuestion;
    setView("ask");
    $("#queryInput").focus();
  } else if (reopen) reopenHistory(reopen.dataset.reopenQuery);
});

$("#detailTabs").addEventListener("click", event => {
  const button = event.target.closest("[data-detail-tab]");
  if (button) setDetailTab(button.dataset.detailTab);
});
$("#backLibrary").onclick = () => setView("documents");
$("#chatDocumentButton").onclick = () => {
  const document = activeDocument();
  if (!document) return;
  selectedQueryDocs = new Set([document.document_id]);
  renderScopeOptions();
  setView("ask");
};
$("#reportButton").onclick = () => window.print();

$("#searchDocs").addEventListener("input", renderRows);
$("#filterType").onchange = renderRows;
$("#filterDomain").onchange = renderRows;
$("#sortDocs").onchange = renderRows;
$("#viewToggle").onclick = () => { gridMode = !gridMode; renderRows(); };
$("#refreshDocs").onclick = async () => { await Promise.all([refreshDocuments(), loadHealthAndConfig()]); };
$("#globalSearch").addEventListener("input", event => {
  setView("documents");
  $("#searchDocs").value = event.target.value;
  renderRows();
});

$("#scopeButton").onclick = () => { $("#scopeMenu").hidden = !$("#scopeMenu").hidden; };
$("#scopeMenu").addEventListener("change", event => {
  const checkbox = event.target.closest("[data-scope-id]");
  if (!checkbox) return;
  if (checkbox.checked) selectedQueryDocs.add(checkbox.dataset.scopeId);
  else selectedQueryDocs.delete(checkbox.dataset.scopeId);
  renderScopeOptions();
});
document.addEventListener("click", event => {
  if (!event.target.closest(".scope-picker") && $("#scopeMenu")) $("#scopeMenu").hidden = true;
});

function makeQueryId() { return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(16).slice(2)}`; }

$("#suggestions").addEventListener("click", event => {
  const button = event.target.closest("button");
  if (button) { $("#queryInput").value = button.textContent.trim(); $("#queryInput").focus(); }
});

$("#askButton").onclick = async () => {
  const query = $("#queryInput").value.trim();
  if (!query) { notify("Enter a question to continue.", true); $("#queryInput").focus(); return; }
  const button = $("#askButton");
  button.disabled = true;
  button.innerHTML = '<span class="spin">◌</span> Working…';
  $("#answerArea").innerHTML = `<article class="card result"><div class="skeleton" style="width:28%;margin-bottom:15px"></div><div class="skeleton" style="width:100%;margin-bottom:9px"></div><div class="skeleton" style="width:82%;margin-bottom:9px"></div><div class="skeleton" style="width:68%"></div></article>`;
  try {
    const response = await api("/query", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query,
        document_ids: selectedQueryDocs.size ? [...selectedQueryDocs] : null,
        enable_verification: $("#verifyToggle").checked,
        enable_research: false,
        session_id: sessionId,
      }),
    });
    const item = {
      id: makeQueryId(), query, answer: response.answer, response,
      document_ids: response.document_ids || [...selectedQueryDocs], intent: response.intent,
      confidence: response.confidence, confidence_score: response.confidence_score,
      execution_time_seconds: response.execution_time_seconds, agent_logs: response.agent_logs || [],
      created_at: new Date().toISOString(), session_id: sessionId,
    };
    saveQuery(item);
    currentConversation.push(item);
    renderQueryResult(item);
    renderDashboard();
  } catch (error) {
    const item = { id: makeQueryId(), query, error: error.message, created_at: new Date().toISOString(), session_id: sessionId, document_ids: [...selectedQueryDocs] };
    saveQuery(item);
    currentConversation.push(item);
    renderQueryResult(item);
    renderDashboard();
  } finally {
    button.disabled = false;
    button.innerHTML = '<svg viewBox="0 0 24 24"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>Ask question';
  }
};

$("#compareButton").onclick = async () => {
  const first = $("#compareA").value;
  const second = $("#compareB").value;
  if (!first || !second) { notify("Select two documents to compare.", true); return; }
  if (first === second) { notify("Choose two different documents.", true); return; }
  const button = $("#compareButton");
  button.disabled = true;
  button.textContent = "Comparing extracted evidence…";
  $("#compareArea").innerHTML = `<article class="card compare-output"><div class="skeleton" style="width:40%;margin-bottom:15px"></div><div class="skeleton" style="width:90%"></div></article>`;
  try {
    const result = await api("/compare", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ doc1_id: first, doc2_id: second }) });
    const metrics = result.metrics || [];
    const metricCards = metrics.map(metric => {
      const change = metric.change_percent == null ? "—" : `${metric.change_percent > 0 ? "+" : ""}${metric.change_percent}%`;
      const number = value => value == null ? "—" : Number(value).toLocaleString(undefined, { maximumFractionDigits: 2 });
      return `<section class="metric comparison-metric"><div class="metric-head"><b>${escapeHtml(metric.metric)}</b><span class="badge">${escapeHtml(change)}</span></div><div class="compare-values"><div><small>${escapeHtml(result.doc1_name)}</small><strong>${number(metric.doc1_value)}</strong></div><div><small>${escapeHtml(result.doc2_name)}</small><strong>${number(metric.doc2_value)}</strong></div></div><div class="compare-evidence"><span>${escapeHtml((metric.doc1_text || "").slice(0, 190))}</span><span>${escapeHtml((metric.doc2_text || "").slice(0, 190))}</span></div></section>`;
    }).join("");
    $("#compareArea").innerHTML = `<article class="card compare-output"><div class="result-meta"><span class="confidence">${metrics.length ? `${metrics.length} comparable metric(s)` : "Text comparison"}</span></div><h2 style="font-size:16px">${escapeHtml(result.doc1_name)} <span class="muted">vs</span> ${escapeHtml(result.doc2_name)}</h2><p class="answer">${escapeHtml(result.comparison_summary)}</p>${metrics.length ? `<h3 class="mini-heading">Extracted metrics and calculated changes</h3><div class="comparison-metric-grid">${metricCards}</div>` : result.key_differences?.length ? `<h3 class="mini-heading">Evidence found in both documents</h3><ul class="fact-list">${result.key_differences.map(value => `<li>${escapeHtml(value)}</li>`).join("")}</ul>` : ""}${result.citations?.length ? `<h3 class="mini-heading">Source evidence</h3><div class="source-list">${result.citations.map(renderSource).join("")}</div>` : `<p class="muted source-unavailable">No citations were returned for this comparison.</p>`}</article>`;
  } catch (error) {
    $("#compareArea").innerHTML = `<article class="card compare-output"><div class="eyebrow" style="color:#c4575b">Comparison failed</div><p style="margin:8px 0 0;color:#586477">${escapeHtml(error.message)}</p></article>`;
  } finally { button.disabled = false; button.textContent = "Compare documents →"; }
};

async function openSummaryFromLibrary(id) {
  const meta = documents.find(item => item.document_id === id);
  if (!meta) return;
  try { await openDocument(meta); setDetailTab("overview"); setView("document-detail"); }
  catch (error) { notify(error.message, true); }
}

const fileInput = $("#fileInput");
const dropZone = $("#dropZone");
$("#browseBtn").onclick = () => fileInput.click();
dropZone.addEventListener("click", event => { if (!event.target.closest("button")) fileInput.click(); });
fileInput.addEventListener("change", () => { if (fileInput.files?.[0]) uploadFile(fileInput.files[0]); });
["dragenter", "dragover"].forEach(type => dropZone.addEventListener(type, event => { event.preventDefault(); dropZone.classList.add("drag"); }));
["dragleave", "drop"].forEach(type => dropZone.addEventListener(type, event => { event.preventDefault(); dropZone.classList.remove("drag"); }));
dropZone.addEventListener("drop", event => { const file = event.dataTransfer?.files?.[0]; if (file) uploadFile(file); });

async function uploadFile(file) {
  const allowed = runtimeConfig?.supported_extensions || [".pdf", ".docx", ".txt", ".csv", ".xlsx"];
  const extension = `.${file.name.split(".").pop()}`.toLowerCase();
  if (!allowed.includes(extension)) { notify(`Unsupported file type. Use ${allowed.join(", ")}.`, true); return; }
  const limit = runtimeConfig?.max_upload_bytes || 50 * 1024 * 1024;
  if (file.size > limit) { notify(`The file exceeds the ${(limit / (1024 * 1024)).toFixed(0)} MiB upload limit.`, true); return; }
  const button = $("#browseBtn");
  button.disabled = true;
  button.innerHTML = '<span class="spin">◌</span> Uploading & indexing…';
  const started = performance.now();
  try {
    const body = new FormData();
    body.append("file", file);
    const result = await api("/upload", { method: "POST", body });
    const meta = result.metadata;
    notify(`${meta.filename} is indexed and ready.`);
    $("#uploadResult").innerHTML = `<article class="card result upload-result"><div class="result-meta"><span class="confidence">Ready · response in ${((performance.now() - started) / 1000).toFixed(1)}s</span></div><h2 style="font-size:15px">${escapeHtml(meta.filename)}</h2><p class="muted" style="font-size:11px">The API completed parsing, classification, chunking, embedding and indexing. Intermediate progress is not exposed by this backend.</p><div class="upload-meta-grid">${[["Type", meta.document_type], ["Domain", meta.domain], ["Heuristic score", `${Math.round((meta.classification_confidence || 0) * 100)}%`], ["Pages", meta.num_pages], ["Chunks", meta.num_chunks], ["Tables", meta.num_tables]].map(([label, value]) => `<div><small>${escapeHtml(label)}</small><b>${escapeHtml(value ?? "—")}</b></div>`).join("")}</div><button class="button outline" data-open="${escapeHtml(meta.document_id)}">Open document details</button></article>`;
    fileInput.value = "";
    await refreshDocuments();
    setView("documents");
  } catch (error) { notify(error.message, true); }
  finally { button.disabled = false; button.textContent = "Choose file"; }
}

$("#clearHistory").onclick = () => {
  if (!window.confirm("Clear the query history saved in this browser?")) return;
  clearQueryHistory(); currentConversation = []; renderHistory(); renderDashboard(); renderAnalytics(); renderAgentRuns();
};
document.addEventListener("click", event => {
  const button = event.target.closest("#themeToggle, #themeToggleSettings");
  if (button) toggleTheme();
});
function toggleTheme() {
  document.body.classList.toggle("dark-theme");
  localStorage.setItem("documind.theme.v1", document.body.classList.contains("dark-theme") ? "dark" : "light");
}
if (localStorage.getItem("documind.theme.v1") === "dark") document.body.classList.add("dark-theme");

$("#searchDocs").value = "";
refreshDocuments();
loadHealthAndConfig();
renderDashboard();
