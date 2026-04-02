import { Configuration } from "@azure/msal-browser";

// These will be fetched from the backend at runtime
let msalConfig: Configuration = {
  auth: {
    clientId: "",
    authority: "https://login.microsoftonline.com/common",
    redirectUri: window.location.origin,
    postLogoutRedirectUri: window.location.origin,
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
};

export const loginRequest = {
  scopes: ["User.Read"],
};

export function updateMsalConfig(clientId: string, tenantId: string) {
  msalConfig = {
    ...msalConfig,
    auth: {
      ...msalConfig.auth,
      clientId,
      authority: `https://login.microsoftonline.com/${tenantId}`,
    },
  };
}

export { msalConfig };
