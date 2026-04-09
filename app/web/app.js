const ingestHistory = [];
let chatWs = null;
let chatHistory = [];

document.addEventListener("DOMContentLoaded", () => {
    loadHealth();
    setupProviderSwitch();
    setupTestButton();
    setupModelSelectors();
    setupChat();
    setupDropZone();
    setupURLIngest();
    setupMaintenance();
    loadWikiTree();
    setupTabs();
    setupWikiViewer();
});

async function loadHealth() {
    try {
        const res = await fetch("/api/health");
        const data = await res.json();

        document.getElementById("machine-name").textContent = data.machine;

        // Status bar badge
        const badge = document.getElementById("provider-badge");
        badge.textContent = data.provider;
        badge.className = "badge provider-ok";

        // System info
        document.getElementById("status-info").innerHTML = `
            <p><span class="label">Machine: </span><span class="value-accent">${data.machine}</span></p>
            <p><span class="label">Provider: </span><span class="value">${data.provider}</span></p>
            <p><span class="label">Data Dir: </span><span class="value">${data.data_dir}</span></p>
            <p><span class="label">Status: </span><span class="value">${data.status}</span></p>
            <p><span class="label">Time: </span><span class="value">${new Date(data.timestamp).toLocaleString()}</span></p>
        `;

        // Provider details
        if (data.providers && data.providers.length > 0) {
            renderProviders(data.providers, data.provider);
        }
    } catch (err) {
        document.getElementById("status-info").innerHTML = `
            <p style="color: var(--error)">Failed to connect to server: ${err.message}</p>
        `;
    }
}

function renderProviders(providers, current) {
    const list = document.getElementById("provider-list");
    if (!list) return;
    list.innerHTML = providers.map(p => `
        <div class="provider-row ${p.name === current ? 'active' : ''}">
            <span class="provider-indicator ${p.available ? 'indicator-ok' : 'indicator-err'}"></span>
            <span class="provider-name">${p.name}</span>
            <span class="provider-model">${p.model}</span>
            <span class="provider-status">${p.status_message}</span>
            ${p.name === current ? '<span class="provider-current">[active]</span>' : ''}
        </div>
    `).join("");

    // Update radio buttons
    const radios = document.querySelectorAll('input[name="provider"]');
    radios.forEach(r => { r.checked = r.value === current; });

    // Update wiki stats badge
    const statsEl = document.getElementById("wiki-stats");
    if (statsEl) statsEl.textContent = current;
}

function setupProviderSwitch() {
    document.querySelectorAll('input[name="provider"]').forEach(radio => {
        radio.addEventListener("change", async (e) => {
            const name = e.target.value;
            const badge = document.getElementById("provider-badge");
            badge.textContent = name + "...";
            badge.className = "badge provider-switching";

            try {
                const res = await fetch("/api/settings/provider", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ provider: name }),
                });
                const data = await res.json();
                if (data.ok) {
                    // Reload full status
                    await loadHealth();
                } else {
                    badge.textContent = "error";
                    badge.className = "badge provider-error";
                }
            } catch (err) {
                badge.textContent = "error";
                badge.className = "badge provider-error";
            }
        });
    });
}

async function setupModelSelectors() {
    try {
        const res = await fetch("/api/models");
        const data = await res.json();

        // Claude models
        const claudeSelect = document.getElementById("claude-model-select");
        if (claudeSelect && data.models.claude) {
            claudeSelect.innerHTML = data.models.claude.map(m =>
                `<option value="${m}" ${m === data.current.claude ? 'selected' : ''}>${m}</option>`
            ).join("");
            claudeSelect.addEventListener("change", () => switchModel("claude", claudeSelect.value));
        }

        // Ollama models
        const ollamaSelect = document.getElementById("ollama-model-select");
        if (ollamaSelect && data.models.ollama) {
            ollamaSelect.innerHTML = data.models.ollama.map(m =>
                `<option value="${m}" ${m === data.current.ollama ? 'selected' : ''}>${m}</option>`
            ).join("");
            ollamaSelect.addEventListener("change", () => switchModel("ollama", ollamaSelect.value));
        }
    } catch (err) {
        // Models endpoint may not be ready yet
    }
}

async function switchModel(provider, model) {
    try {
        const res = await fetch("/api/settings/model", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ provider, model }),
        });
        const data = await res.json();
        if (data.ok) {
            await loadHealth();
        }
    } catch (err) {
        console.error("Failed to switch model:", err);
    }
}

function setupTestButton() {
    const btn = document.getElementById("test-llm-btn");
    if (!btn) return;

    btn.addEventListener("click", async () => {
        const resultEl = document.getElementById("test-result");
        resultEl.classList.remove("hidden");
        resultEl.textContent = "Testing...";
        resultEl.className = "test-result";

        try {
            const res = await fetch("/api/test-llm");
            const data = await res.json();
            if (data.ok) {
                resultEl.textContent = `[${data.provider}/${data.model}] ${data.response}`;
                resultEl.className = "test-result test-ok";
            } else {
                resultEl.textContent = `[${data.provider}] Error: ${data.error}`;
                resultEl.className = "test-result test-err";
            }
        } catch (err) {
            resultEl.textContent = `Request failed: ${err.message}`;
            resultEl.className = "test-result test-err";
        }
    });
}

// --- Ingest ---

function setupDropZone() {
    const zone = document.getElementById("drop-zone");
    if (!zone) return;

    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("drag-over");
    });

    zone.addEventListener("drop", async (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");

        const files = e.dataTransfer.files;
        if (files.length === 0) return;

        const subdir = document.getElementById("subdir-select").value;
        for (const file of files) {
            await uploadFile(file, subdir);
        }
    });
}

function setupURLIngest() {
    const btn = document.getElementById("ingest-url-btn");
    const input = document.getElementById("url-input");
    if (!btn || !input) return;

    const doIngest = async () => {
        const url = input.value.trim();
        if (!url) return;
        input.value = "";
        const subdir = document.getElementById("subdir-select").value;
        await ingestURL(url, subdir);
    };

    btn.addEventListener("click", doIngest);
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") doIngest();
    });
}

async function uploadFile(file, subdir) {
    showIngestStatus(`Ingesting ${file.name}...`);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("subdir", subdir);

    try {
        const res = await fetch("/api/ingest/file", { method: "POST", body: formData });
        const data = await res.json();
        if (data.ok) {
            addIngestEntry(data);
            showIngestStatus(`Ingested: ${data.filename}`, "ok");
        } else {
            showIngestStatus(`Error: ${data.error}`, "err");
        }
    } catch (err) {
        showIngestStatus(`Failed: ${err.message}`, "err");
    }
}

async function ingestURL(url, subdir) {
    showIngestStatus(`Ingesting URL...`);
    try {
        const res = await fetch("/api/ingest/url", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url, subdir }),
        });
        const data = await res.json();
        if (data.ok) {
            addIngestEntry(data);
            showIngestStatus(`Ingested: ${data.filename}`, "ok");
        } else {
            showIngestStatus(`Error: ${data.error}`, "err");
        }
    } catch (err) {
        showIngestStatus(`Failed: ${err.message}`, "err");
    }
}

function showIngestStatus(msg, type = "") {
    const el = document.getElementById("ingest-status");
    el.classList.remove("hidden");
    el.textContent = msg;
    el.className = `ingest-status ${type === "ok" ? "status-ok" : type === "err" ? "status-err" : ""}`;
}

function addIngestEntry(data) {
    ingestHistory.unshift(data);
    if (ingestHistory.length > 5) ingestHistory.pop();
    renderIngestHistory();
}

function renderIngestHistory() {
    const list = document.getElementById("ingest-list");
    if (!list) return;
    list.innerHTML = ingestHistory.map(e => `
        <div class="ingest-entry">
            <span class="ingest-type">[${e.source_type}]</span>
            <span class="ingest-file">${e.filename}</span>
            <span class="ingest-path">${e.raw_path}</span>
        </div>
    `).join("");
}

// --- Chat ---

function setupChat() {
    const input = document.getElementById("chat-input");
    const btn = document.getElementById("chat-send-btn");
    if (!input || !btn) return;

    connectChatWs();

    const send = () => {
        const text = input.value.trim();
        if (!text || !chatWs || chatWs.readyState !== WebSocket.OPEN) return;
        input.value = "";
        appendChatBubble("user", text);

        // Send with history (last 10 turns for context)
        const recentHistory = chatHistory.slice(-10);
        chatWs.send(JSON.stringify({
            type: "user_message",
            content: text,
            history: recentHistory,
        }));

        chatHistory.push({ role: "user", content: text });
        startAssistantBubble();
    };

    btn.addEventListener("click", send);
    input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
        }
    });
}

function connectChatWs() {
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    chatWs = new WebSocket(`${protocol}//${location.host}/ws/chat`);

    chatWs.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        handleChatEvent(msg);
    };

    chatWs.onclose = () => {
        setTimeout(connectChatWs, 2000);
    };

    chatWs.onerror = () => {
        // Will trigger onclose
    };
}

let currentAssistantEl = null;
let currentToolsEl = null;
let assistantText = "";

function startAssistantBubble() {
    assistantText = "";
    const container = document.getElementById("chat-messages");

    const bubble = document.createElement("div");
    bubble.className = "chat-bubble assistant";

    currentToolsEl = document.createElement("div");
    currentToolsEl.className = "tool-calls";
    bubble.appendChild(currentToolsEl);

    currentAssistantEl = document.createElement("div");
    currentAssistantEl.className = "bubble-content";
    currentAssistantEl.textContent = "Thinking...";
    bubble.appendChild(currentAssistantEl);

    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function handleChatEvent(msg) {
    const container = document.getElementById("chat-messages");

    if (msg.type === "tool_call_started" && currentToolsEl) {
        const el = document.createElement("div");
        el.className = "tool-indicator";
        el.textContent = `Reading ${msg.data.args?.path || msg.data.name}...`;
        el.id = `tool-${msg.data.name}-${Date.now()}`;
        currentToolsEl.appendChild(el);
        container.scrollTop = container.scrollHeight;
    }

    if (msg.type === "tool_call_finished" && currentToolsEl) {
        const indicators = currentToolsEl.querySelectorAll(".tool-indicator");
        const last = indicators[indicators.length - 1];
        if (last) {
            last.textContent = `Read ${msg.data.name}: ${msg.data.preview?.substring(0, 60) || "done"}...`;
            last.classList.add("tool-done");
        }
    }

    if (msg.type === "token" && currentAssistantEl) {
        if (assistantText === "") {
            currentAssistantEl.textContent = "";
        }
        assistantText += msg.data;
        currentAssistantEl.innerHTML = renderMarkdown(assistantText);
        container.scrollTop = container.scrollHeight;
    }

    if (msg.type === "done") {
        if (assistantText) {
            chatHistory.push({ role: "assistant", content: assistantText });
        }
        currentAssistantEl = null;
        currentToolsEl = null;
    }

    if (msg.type === "error") {
        if (currentAssistantEl) {
            currentAssistantEl.textContent = `Error: ${msg.data}`;
            currentAssistantEl.classList.add("chat-error");
        }
        currentAssistantEl = null;
        currentToolsEl = null;
    }
}

function appendChatBubble(role, text) {
    const container = document.getElementById("chat-messages");
    const bubble = document.createElement("div");
    bubble.className = `chat-bubble ${role}`;

    const content = document.createElement("div");
    content.className = "bubble-content";
    content.innerHTML = role === "user" ? escapeHtml(text) : renderMarkdown(text);
    bubble.appendChild(content);

    container.appendChild(bubble);
    container.scrollTop = container.scrollHeight;
}

function renderMarkdown(text) {
    // Simple markdown rendering
    return text
        .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
        .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
        .replace(/\*(.+?)\*/g, "<em>$1</em>")
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<span class="wiki-ref">[$1]</span>')
        .replace(/^### (.+)$/gm, '<h4>$1</h4>')
        .replace(/^## (.+)$/gm, '<h3>$1</h3>')
        .replace(/^# (.+)$/gm, '<h2>$1</h2>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/\n/g, "<br>");
}

function escapeHtml(text) {
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// --- Wiki Tree ---

async function loadWikiTree() {
    try {
        const res = await fetch("/api/wiki/tree");
        const tree = await res.json();
        const container = document.getElementById("wiki-tree");
        if (!container) return;
        container.innerHTML = renderTree(tree, "");
    } catch (err) {
        // Wiki may be empty on first run
    }

    const btn = document.getElementById("wiki-refresh-btn");
    if (btn) btn.addEventListener("click", loadWikiTree);
}

function renderTree(node, basePath) {
    if (node.type === "file") {
        const path = basePath ? `${basePath}/${node.name}` : node.name;
        return `<span class="tree-file" data-path="${path}" onclick="openWikiFile('${path}')">${node.name}</span>`;
    }

    if (!node.children || node.children.length === 0) return "";

    const dirName = node.name === "wiki" ? "" : node.name;
    const childPath = basePath ? `${basePath}/${node.name}` : node.name;
    const childrenHtml = node.children
        .map(c => renderTree(c, node.name === "wiki" ? "" : childPath))
        .filter(Boolean)
        .join("");

    if (node.name === "wiki") {
        return childrenHtml;
    }

    return `<div class="tree-dir">
        <div class="tree-dir-name">${node.name}/</div>
        <div class="tree-children">${childrenHtml}</div>
    </div>`;
}

// --- Wiki Viewer ---

function setupWikiViewer() {
    const closeBtn = document.getElementById("wiki-viewer-close");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => {
            document.getElementById("wiki-viewer").classList.add("hidden");
        });
    }
}

async function openWikiFile(path) {
    try {
        const res = await fetch(`/api/wiki/rendered?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        if (!data.ok) return;

        document.getElementById("wiki-viewer-title").textContent = path;
        document.getElementById("wiki-viewer-content").innerHTML = data.html;
        document.getElementById("wiki-viewer").classList.remove("hidden");
    } catch (err) {
        console.error("Failed to load wiki file:", err);
    }
}

// Global function for wiki links in rendered content
function viewWikiLink(href) {
    // Normalize relative paths
    const clean = href.replace(/^\.\.\//g, "").replace(/^\.\//, "");
    openWikiFile(clean);
}

// --- Tabs ---

function setupTabs() {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.dataset.tab;
            document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
            document.querySelectorAll(".tab-content").forEach(t => t.classList.remove("active"));
            btn.classList.add("active");
            document.getElementById(targetId)?.classList.add("active");
        });
    });
}

// --- Maintenance (Snapshot + Lint) ---

function setupMaintenance() {
    const snapBtn = document.getElementById("snapshot-btn");
    const lintBtn = document.getElementById("lint-btn");

    if (snapBtn) {
        snapBtn.addEventListener("click", async () => {
            showActionStatus("Creating snapshot...");
            try {
                const res = await fetch("/api/snapshot/create", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ reason: "manual" }),
                });
                const data = await res.json();
                if (data.ok) {
                    showActionStatus(`Snapshot created: ${data.snapshot.id} (${data.snapshot.size_mb}MB)`, "ok");
                    loadSnapshots();
                } else {
                    showActionStatus(`Error: ${data.error}`, "err");
                }
            } catch (err) {
                showActionStatus(`Failed: ${err.message}`, "err");
            }
        });
    }

    if (lintBtn) {
        lintBtn.addEventListener("click", async () => {
            showActionStatus("Running lint...");
            try {
                const res = await fetch("/api/lint/run", { method: "POST" });
                const data = await res.json();
                if (data.ok) {
                    showActionStatus(`Lint report: ${data.report}`, "ok");
                    // Refresh wiki tree to show new report
                    loadWikiTree();
                    // Open the report
                    openWikiFile(`_reports/${data.report}`);
                } else {
                    showActionStatus(`Error: ${data.error}`, "err");
                }
            } catch (err) {
                showActionStatus(`Failed: ${err.message}`, "err");
            }
        });
    }

    loadSnapshots();
}

function showActionStatus(msg, type = "") {
    const el = document.getElementById("action-status");
    if (!el) return;
    el.classList.remove("hidden");
    el.textContent = msg;
    el.className = `action-status ${type === "ok" ? "status-ok" : type === "err" ? "status-err" : ""}`;
}

async function loadSnapshots() {
    try {
        const res = await fetch("/api/snapshot/list");
        const data = await res.json();
        const list = document.getElementById("snapshots-list");
        if (!list || !data.snapshots) return;
        if (data.snapshots.length === 0) {
            list.innerHTML = '<p class="dim-text">No snapshots yet</p>';
            return;
        }
        list.innerHTML = '<h4>> Snapshots</h4>' + data.snapshots.map(s => `
            <div class="snapshot-entry">
                <span class="snapshot-id">${s.id}</span>
                <span class="snapshot-size">${s.size_mb}MB</span>
            </div>
        `).join("");
    } catch (err) {
        // ignore
    }
}
