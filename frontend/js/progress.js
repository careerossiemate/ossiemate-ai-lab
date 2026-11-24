import {
    getProgress,
    saveProgress
} from "./api-client.js";


const exerciseIds = ["03", "04", "05", "06"];

let records = new Map();

let authorised = false;

let busy = false;

let loaded = false;


function getElements() {

    return {

        panel: document.getElementById("progress-panel"),

        exercise: document.getElementById("progress-exercise"),

        percentage: document.getElementById("progress-percentage"),

        percentageValue: document.getElementById("progress-value"),

        status: document.getElementById("progress-status"),

        notes: document.getElementById("progress-notes"),

        saveButton: document.getElementById("save-progress"),

        refreshButton: document.getElementById("refresh-progress"),

        summary: document.getElementById("progress-summary")

    };

}


function deriveStatus(percentage) {

    if (percentage === 100) {
        return "completed";
    }

    if (percentage === 0) {
        return "not_started";
    }

    return "in_progress";

}


function statusLabel(status) {

    const labels = {

        not_started: "Not started",

        in_progress: "In progress",

        completed: "Completed"

    };

    return labels[status] || "Unknown";

}


function updateFormStatus() {

    const ui = getElements();

    const percentage = Number(ui.percentage.value);

    ui.percentageValue.textContent =
        `${percentage}%`;

    ui.status.textContent =
        statusLabel(deriveStatus(percentage));

}


function updateProgressCards() {

    for (const id of exerciseIds) {

        const record = records.get(id);

        const percentage =
            record?.CompletionPercentage ?? 0;

        const bar =
            document.getElementById(`progress-bar-${id}`);

        const label =
            document.getElementById(`progress-label-${id}`);

        if (bar) {
            bar.value = percentage;
        }

        if (label) {

            label.textContent =
                `${percentage}% - ${statusLabel(
                    record?.Status || "not_started"
                )}`;

        }

    }

}


function populateSelectedExercise() {

    const ui = getElements();

    const record = records.get(ui.exercise.value);

    ui.percentage.value =
        record?.CompletionPercentage ?? 0;

    ui.notes.value =
        record?.Notes ?? "";

    updateFormStatus();

}


function setBusy(value) {

    busy = value;

    const ui = getElements();

    ui.saveButton.disabled =
        busy || !authorised || !loaded;

    ui.refreshButton.disabled =
        busy || !authorised;

    ui.exercise.disabled =
        busy || !authorised || !loaded;

    ui.percentage.disabled =
        busy || !authorised || !loaded;

    ui.notes.disabled =
        busy || !authorised || !loaded;

}


async function refreshProgress() {

    if (!authorised || busy) {
        return;
    }

    const ui = getElements();

    loaded = false;

    setBusy(true);

    ui.summary.textContent =
        "Retrieving progress from Azure Table Storage...";

    try {

        const result = await getProgress();

        if (!Array.isArray(result.progress)) {
            throw new Error("Invalid progress response.");
        }

        records = new Map(
            result.progress.map(
                record => [record.ExerciseId, record]
            )
        );

        updateProgressCards();

        populateSelectedExercise();

        loaded = true;

        ui.summary.textContent =
            `Retrieved ${result.progress.length} saved progress records.`;

    } catch (error) {

        ui.summary.textContent =
            error.message || "Unable to retrieve progress.";

    } finally {

        setBusy(false);

    }

}


async function submitProgress() {

    if (!authorised || busy || !loaded) {
        return;
    }

    const ui = getElements();

    const exerciseId = ui.exercise.value;

    const percentage = Number(ui.percentage.value);

    const notes = ui.notes.value.trim();

    if (
        !exerciseIds.includes(exerciseId) ||
        !Number.isInteger(percentage) ||
        percentage < 0 ||
        percentage > 100 ||
        notes.length > 2000
    ) {

        ui.summary.textContent =
            "Please enter valid exercise progress.";

        return;

    }

    setBusy(true);

    ui.summary.textContent =
        "Saving progress to Azure Table Storage...";

    try {

        await saveProgress(

            exerciseId,

            deriveStatus(percentage),

            percentage,

            notes

        );

    } catch (error) {

        loaded = false;

        ui.summary.textContent =
            "Save could not be confirmed. Refresh before retrying. "
            + (error.message || "");

        setBusy(false);

        return;

    }

    setBusy(false);

    await refreshProgress();

}


export function initializeProgressUI(isAuthorised) {

    const ui = getElements();

    if (Object.values(ui).some(element => !element)) {
        return;
    }

    authorised = isAuthorised === true;

    loaded = false;

    ui.panel.hidden = !authorised;

    ui.exercise.onchange =
        authorised ? populateSelectedExercise : null;

    ui.percentage.oninput =
        authorised ? updateFormStatus : null;

    ui.saveButton.onclick =
        authorised ? submitProgress : null;

    ui.refreshButton.onclick =
        authorised ? refreshProgress : null;

    setBusy(false);

    if (authorised) {

        refreshProgress();

    } else {

        records.clear();

        ui.notes.value = "";

    }

}
