export const runtimeConfig = Object.freeze({

    applicationName: "Ossiemate AI Lab",

    environment: "development",

    apiBaseUrl: "",

    liveBackendEnabled: false,

    requestTimeoutMs: 150000,

    endpoints: {

        health: "/health",

        info: "/api/info",

        exercises: "/api/exercises",

        currentUser: "/api/auth/me",

        diagnostics: "/api/diagnostics",

        progress: "/api/progress"

    }

});
