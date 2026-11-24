export const runtimeConfig = Object.freeze({

    applicationName: "Ossiemate AI Lab",

    environment: "development",

    apiBaseUrl: "https://ca-ai103-backend.wittywave-5f5679ff.australiaeast.azurecontainerapps.io",

    liveBackendEnabled: true,

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
