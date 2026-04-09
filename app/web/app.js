document.addEventListener("DOMContentLoaded", () => {
    loadHealth();
    setupProviderSwitch();
    setupTestButton();
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
    const detail = document.getElementById("provider-detail");
    detail.classList.remove("hidden");

    const list = document.getElementById("provider-list");
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
    const switchEl = document.getElementById("provider-switch");
    switchEl.classList.remove("hidden");
    const radios = switchEl.querySelectorAll('input[name="provider"]');
    radios.forEach(r => { r.checked = r.value === current; });
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
