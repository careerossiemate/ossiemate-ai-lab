import {
    getAccessToken
} from "./auth.js";

import {
    runtimeConfig
} from "./runtime-config.js";


// Custom API error.

export class ApiError extends Error {

    constructor(message, status = 0) {

        super(message);

        this.name = "ApiError";

        this.status = status;

    }

}


// Check whether backend connectivity is configured.

export function isBackendConfigured() {

    return Boolean(

        runtimeConfig.liveBackendEnabled &&

        runtimeConfig.apiBaseUrl

    );

}


// Construct and validate the backend URL.

function buildApiUrl(endpoint) {

    if (!isBackendConfigured()) {

        throw new ApiError(
            "Live AI backend is currently offline."
        );

    }

    const baseUrl = new URL(
        runtimeConfig.apiBaseUrl
    );

    if (
        baseUrl.protocol !== "https:" ||
        baseUrl.username ||
        baseUrl.password
    ) {

        throw new ApiError(
            "Invalid backend configuration."
        );

    }

    const allowedEndpoints = Object.values(
        runtimeConfig.endpoints
    );

    if (!allowedEndpoints.includes(endpoint)) {

        throw new ApiError(
            "Unsupported API endpoint."
        );

    }

    const url = new URL(
        endpoint,
        baseUrl.origin
    );

    if (url.origin !== baseUrl.origin) {

        throw new ApiError(
            "Invalid API destination."
        );

    }

    return url.toString();

}


// Central HTTP request function.

async function request(
    endpoint,
    {
        method = "GET",
        authenticated = false,
        body = null
    } = {}
) {

    const url = buildApiUrl(endpoint);

    const headers = {

        "Accept": "application/json"

    };

    if (authenticated) {

        const token = await getAccessToken();

        headers["Authorization"] =
            `Bearer ${token}`;

    }

    if (body !== null) {

        headers["Content-Type"] =
            "application/json";

    }

    const controller =
        new AbortController();

    const timeout = setTimeout(

        () => controller.abort(),

        runtimeConfig.requestTimeoutMs

    );

    try {

        const response = await fetch(url, {

            method: method,

            headers: headers,

            body: body === null
                ? undefined
                : JSON.stringify(body),

            signal: controller.signal,

            credentials: "omit",

            redirect: "error",

            cache: "no-store"

        });

        if (!response.ok) {

            let message =
                `API request failed (${response.status}).`;

            switch (response.status) {

                case 401:
                    message =
                        "Authentication required. Please sign in again.";
                    break;

                case 403:
                    message =
                        "You are not authorised to access this operation.";
                    break;

                case 404:
                    message =
                        "The requested API endpoint is unavailable.";
                    break;

                case 422:
                    message =
                        "The submitted information is invalid.";
                    break;

                case 429:
                    message =
                        "Request limit reached. Please try again later.";
                    break;

                case 503:
                    message =
                        "The backend service is temporarily unavailable.";
                    break;

            }

            throw new ApiError(
                message,
                response.status
            );

        }

        return await response.json();

    } catch (error) {

        if (error instanceof ApiError) {

            throw error;

        }

        if (error.name === "AbortError") {

            throw new ApiError(
                "The backend request timed out."
            );

        }

        throw new ApiError(
            "Unable to communicate with the Azure backend."
        );

    } finally {

        clearTimeout(timeout);

    }

}


// Public API functions.

export function getHealth() {

    return request(
        runtimeConfig.endpoints.health
    );

}


export function getApplicationInfo() {

    return request(
        runtimeConfig.endpoints.info
    );

}


export function getExercises() {

    return request(
        runtimeConfig.endpoints.exercises
    );

}


// Protected API functions.

export function getCurrentUser() {

    return request(

        runtimeConfig.endpoints.currentUser,

        { authenticated: true }

    );

}


export function getDiagnostics() {

    return request(

        runtimeConfig.endpoints.diagnostics,

        { authenticated: true }

    );

}


export function getProgress() {

    return request(

        runtimeConfig.endpoints.progress,

        { authenticated: true }

    );

}


export function saveProgress(
    exerciseId,
    status,
    completionPercentage,
    notes = ""
) {

    return request(

        runtimeConfig.endpoints.progress,

        {

            method: "POST",

            authenticated: true,

            body: {

                exercise_id: exerciseId,

                status: status,

                completion_percentage:
                    completionPercentage,

                notes: notes

            }

        }

    );

}
