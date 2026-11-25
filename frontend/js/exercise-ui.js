import { getAccessToken } from "./auth.js";
import { runtimeConfig } from "./runtime-config.js";

async function call(path, body) {
    const base = new URL(runtimeConfig.apiBaseUrl);
    if (base.protocol !== "https:" || base.username || base.password ||
        !base.hostname.endsWith(".azurecontainerapps.io")) {
        throw new Error("Invalid backend configuration.");
    }
    const token = await getAccessToken();
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 150000);
    try {
        const response = await fetch(new URL(path, base), {
            method: body ? "POST" : "GET",
            headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"},
            body: body ? JSON.stringify(body) : undefined,
            credentials: "omit", redirect: "error", cache: "no-store", signal: controller.signal
        });
        if (!response.ok) throw new Error(`Request failed (${response.status}).`);
        return await response.json();
    } finally { clearTimeout(timer); }
}

export async function initializeExerciseUI(authorised) {
    const panel = document.getElementById("live-exercise-panel");
    if (!panel) return;
    const button = panel.querySelector("button[data-run]");
    const status = panel.querySelector("[data-status]");
    if (!button) return;
    button.disabled = true;
    button.onclick = null;
    if (!authorised) { status.textContent = "Sign in with an authorised account."; return; }
    try {
        const capabilities = await call("/api/lab/capabilities");
        if (!capabilities["03"]) { status.textContent = "Awaiting cloud validation."; return; }
        let conversation = null;
        const profile = panel.querySelector("select");
        const reset = panel.querySelector("[data-reset]");
        profile.onchange = () => { conversation = null; };
        reset.onclick = () => { conversation = null; status.textContent = "New conversation."; };
        button.disabled = false;
        status.textContent = "Ready.";
        button.onclick = async () => {
            button.disabled = true; profile.disabled = true; reset.disabled = true;
            try {
                const result = await call("/api/lab/03/run", {
                    prompt: panel.querySelector("textarea").value,
                    profile: profile.value, conversation_id: conversation
                });
                conversation = result.conversation_id;
                panel.querySelector("pre").textContent = result.response || "No visible response.";
                status.textContent = `${result.status}: ${result.total_tokens} tokens; ${result.execution_time_seconds}s`;
            } catch (error) { status.textContent = error.message; }
            finally { button.disabled = false; profile.disabled = false; reset.disabled = false; }
        };
    } catch (error) { status.textContent = error.message; }
}
