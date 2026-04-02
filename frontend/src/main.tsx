import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { msalConfig, updateMsalConfig } from "./auth/msalConfig";
import { AuthProvider } from "./auth/AuthContext";
import App from "./App";
import "./index.css";

function Root() {
  const [msalInstance, setMsalInstance] = useState<PublicClientApplication | null>(null);
  const [ssoEnabled, setSsoEnabled] = useState<boolean | null>(null);

  useEffect(() => {
    fetch("/api/auth/config")
      .then((r) => r.json())
      .then((cfg) => {
        if (cfg.enabled && cfg.client_id) {
          updateMsalConfig(cfg.client_id, cfg.tenant_id);
          const instance = new PublicClientApplication(msalConfig);
          instance.initialize().then(() => {
            setMsalInstance(instance);
            setSsoEnabled(true);
          });
        } else {
          setSsoEnabled(false);
        }
      })
      .catch(() => setSsoEnabled(false));
  }, []);

  if (ssoEnabled === null) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    );
  }

  if (!ssoEnabled) {
    return (
      <BrowserRouter>
        <App />
      </BrowserRouter>
    );
  }

  return (
    <MsalProvider instance={msalInstance!}>
      <AuthProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </AuthProvider>
    </MsalProvider>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>
);
