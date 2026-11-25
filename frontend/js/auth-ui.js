import { initializeSpecialised } from "./specialised.js";
import { initializeModules } from './modules.js';
import { initializeExerciseUI } from "./exercise-ui.js";
import {
    initializeProgressUI
} from "./progress.js";

import {
    initializeDiagnosticsUI
} from "./diagnostics.js";

import {
    isBackendConfigured,
    getHealth,
    getCurrentUser
} from "./api-client.js";

import {
    initializeAuth,
    getAuthStatus,
    signIn,
    signOut
} from "./auth.js";

import {
    runtimeConfig
} from "./runtime-config.js";


async function initializeAuthUI() {

    initializeDiagnosticsUI(false);
    initializeProgressUI(false);

    const status =
        document.getElementById("auth-status");

    const profile =
        document.getElementById("auth-profile");

    const signInButton =
        document.getElementById("sign-in-button");

    const signOutButton =
        document.getElementById("sign-out-button");

    const backendStatus =
        document.getElementById("backend-status");

    if (
        !status ||
        !profile ||
        !signInButton ||
        !signOutButton ||
        !backendStatus
    ) {

        return;

    }


    signInButton.addEventListener(
        "click",
        async () => {

            signInButton.disabled = true;

            status.textContent =
                "Connecting to Microsoft...";

            try {

                await signIn();

            } catch (error) {

                status.textContent =
                    "Sign-in failed. Please try again.";

                signInButton.disabled = false;

            }

        }
    );


    signOutButton.addEventListener(
        "click",
        async () => {

            signOutButton.disabled = true;

            status.textContent =
                "Signing out...";

            try {

                await signOut();

            } catch (error) {

                status.textContent =
                    "Sign-out failed. Please try again.";

                signOutButton.disabled = false;

            }

        }
    );


    try {

        await initializeAuth();

        const authStatus = await getAuthStatus();

        if (authStatus.authenticated) {

            status.textContent =
                "Microsoft account connected";

            profile.textContent =
                authStatus.user.name;

            signInButton.hidden = true;

            signOutButton.hidden = false;

            signOutButton.disabled = false;

        } else {

            status.textContent =
                "Public showcase mode";

            profile.textContent =
                "Sign in to access protected demonstrations.";

            signInButton.hidden = false;

            signInButton.disabled = false;

            signOutButton.hidden = true;

        }


        if (!isBackendConfigured()) {

            backendStatus.textContent =
                "Live AI backend is offline.";

        } else {

            try {

                const health = await getHealth();

                if (health.status !== "healthy") {

                    backendStatus.textContent =
                        "Backend health verification failed.";

                } else if (!authStatus.authenticated) {

                    backendStatus.textContent =
                        "Backend available. Microsoft sign-in required.";

                } else {

                    const user = await getCurrentUser();

                    initializeDiagnosticsUI(user.authorised === true);
                    initializeProgressUI(user.authorised === true);
    initializeExerciseUI(user.authorised === true);
initializeModules(user.authorised === true);

                    backendStatus.textContent =
                        user.authorised === true
                            ? "Backend connected. User authorised."
                            : "Live AI access not authorised.";

                }

            } catch (error) {

                backendStatus.textContent =
                    error.message;

            }

        }

    } catch (error) {

        status.textContent =
            "Authentication service unavailable.";

        profile.textContent =
            "Public showcase remains available.";

        signInButton.disabled = true;

        signOutButton.hidden = true;

        backendStatus.textContent =
            "Live AI access unavailable.";

    }

}


initializeAuthUI();
