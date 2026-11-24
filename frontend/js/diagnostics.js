import {
    getDiagnostics
} from "./api-client.js";


const diagnosticServices = {

    managed_identity: "diagnostic-identity",

    blob_storage: "diagnostic-blob",

    table_storage: "diagnostic-table",

    foundry_model: "diagnostic-foundry"

};


function updateDiagnosticStatus(service, value) {

    const elementId = diagnosticServices[service];

    const element = document.getElementById(elementId);

    if (!element) {

        return;

    }

    const labels = {

        connected: "Connected",

        failed: "Failed",

        not_tested: "Not tested"

    };

    element.textContent =
        labels[value] || "Unknown";

    element.dataset.status = value;

}


async function runDiagnostics() {

    const button =
        document.getElementById("run-diagnostics");

    const summary =
        document.getElementById("diagnostics-summary");

    if (!button || !summary) {

        return;

    }

    button.disabled = true;

    summary.textContent =
        "Running infrastructure diagnostics...";

    for (const service of Object.keys(diagnosticServices)) {

        updateDiagnosticStatus(service, "not_tested");

    }

    try {

        const result = await getDiagnostics();

        for (const service of Object.keys(diagnosticServices)) {

            updateDiagnosticStatus(
                service,
                result.checks?.[service] || "unknown"
            );

        }

        summary.textContent =
            result.status === "healthy"
                ? "Infrastructure connectivity checks passed. Foundry model execution is not tested."
                : "One or more infrastructure checks failed.";

    } catch (error) {

        summary.textContent =
            error.message || "Diagnostics failed.";

    } finally {

        button.disabled = false;

    }

}


export function initializeDiagnosticsUI(authorised) {

    const panel =
        document.getElementById("diagnostics-panel");

    const button =
        document.getElementById("run-diagnostics");

    if (!panel || !button) {

        return;

    }

    panel.hidden = authorised !== true;

    button.disabled = authorised !== true;

    button.onclick =
        authorised === true
            ? runDiagnostics
            : null;

}
