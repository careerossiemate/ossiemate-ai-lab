import {
    PublicClientApplication,
    InteractionRequiredAuthError
} from "@azure/msal-browser";

import {
    msalConfig,
    loginRequest,
    tokenRequest
} from "./auth-config.js";


const msalInstance = new PublicClientApplication(
    msalConfig
);

let initializationPromise = null;


// Initialise MSAL and restore authentication session.

export function initializeAuth() {

    if (!initializationPromise) {

        initializationPromise = (async () => {

            await msalInstance.initialize();

            const response =
                await msalInstance.handleRedirectPromise();

            if (response?.account) {

                msalInstance.setActiveAccount(
                    response.account
                );

            }

            if (!msalInstance.getActiveAccount()) {

                const accounts =
                    msalInstance.getAllAccounts();

                if (accounts.length === 1) {

                    msalInstance.setActiveAccount(
                        accounts[0]
                    );

                }

            }

            return getCurrentAccount();

        })().catch(error => {

            initializationPromise = null;

            throw error;

        });

    }

    return initializationPromise;

}


// Retrieve the currently active account.

export function getCurrentAccount() {

    return msalInstance.getActiveAccount();

}


// Check whether a Microsoft account session exists.

export function isAuthenticated() {

    return Boolean(getCurrentAccount());

}


// Retrieve basic profile information.

export function getUserProfile() {

    const account = getCurrentAccount();

    if (!account) {

        return null;

    }

    return {

        name: account.name || account.username,

        username: account.username,

        tenantId: account.tenantId,

        accountId: account.localAccountId

    };

}


// Initiate Microsoft Entra login.

export async function signIn() {

    await initializeAuth();

    await msalInstance.loginRedirect({

        ...loginRequest,

        prompt: "select_account"

    });

}


// End the current Microsoft session.

export async function signOut() {

    await initializeAuth();

    const account = getCurrentAccount();

    if (!account) {

        return;

    }

    await msalInstance.logoutRedirect({

        account: account,

        postLogoutRedirectUri:
            msalConfig.auth.postLogoutRedirectUri

    });

}


// Acquire an access token for the protected API.

export async function getAccessToken() {

    await initializeAuth();

    const account = getCurrentAccount();

    if (!account) {

        throw new Error(
            "Microsoft sign-in is required."
        );

    }

    try {

        const response =
            await msalInstance.acquireTokenSilent({

                ...tokenRequest,

                account: account

            });

        return response.accessToken;

    } catch (error) {

        if (
            error instanceof InteractionRequiredAuthError
        ) {

            throw new Error(
                "Additional authentication is required. Please sign in again.",
                { cause: error }
            );

        }

        throw error;

    }

}


// Return authentication status to the website.

export async function getAuthStatus() {

    await initializeAuth();

    return {

        authenticated: isAuthenticated(),

        user: getUserProfile()

    };

}


// Process authentication redirects on page load.

initializeAuth().catch(() => {

    console.error(
        "Microsoft authentication initialization failed."
    );

});
