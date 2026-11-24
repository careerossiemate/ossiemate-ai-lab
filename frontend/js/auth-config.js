export const msalConfig = {

    auth: {

        clientId: "e440cb90-2d63-49ba-ae76-57501cdd6e4b",

        authority:
            "https://login.microsoftonline.com/8d85034f-9f68-47ed-ad94-9cce4e5b9033",

        redirectUri:
            "https://mango-sea-0589cd400.6.azurestaticapps.net/",

        postLogoutRedirectUri:
            "https://mango-sea-0589cd400.6.azurestaticapps.net/",

        navigateToLoginRequestUrl: true

    },

    cache: {

        cacheLocation: "sessionStorage"

    }

};


export const apiScopes = [

    "api://020082e2-ad12-481e-9c72-fba2d53032b6/access_as_user"

];


export const loginRequest = {

    scopes: apiScopes

};


export const tokenRequest = {

    scopes: apiScopes

};
