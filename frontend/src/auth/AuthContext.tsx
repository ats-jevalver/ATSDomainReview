import { createContext, useContext, useState, useEffect, type ReactNode } from "react";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { loginRequest } from "./msalConfig";
import axios from "axios";

export interface UserProfile {
  oid: string;
  name: string;
  email: string;
  title: string | null;
  phone: string | null;
}

interface AuthContextValue {
  user: UserProfile | null;
  loading: boolean;
  ssoEnabled: boolean;
  login: () => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: false,
  ssoEnabled: false,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isAuthenticated || accounts.length === 0) {
      setUser(null);
      setLoading(false);
      return;
    }

    // Get access token silently and send to backend
    instance
      .acquireTokenSilent({ ...loginRequest, account: accounts[0] })
      .then(async (response) => {
        const { data } = await axios.post<UserProfile>("/api/auth/login", {
          access_token: response.accessToken,
        });
        setUser(data);
        // Store token for API calls
        sessionStorage.setItem("ats_token", response.accessToken);
      })
      .catch((err) => {
        console.error("Token acquisition failed", err);
        setUser(null);
        sessionStorage.removeItem("ats_token");
      })
      .finally(() => setLoading(false));
  }, [isAuthenticated, accounts, instance]);

  const login = () => {
    instance.loginRedirect(loginRequest);
  };

  const logout = () => {
    sessionStorage.removeItem("ats_token");
    setUser(null);
    instance.logoutRedirect();
  };

  return (
    <AuthContext.Provider value={{ user, loading, ssoEnabled: true, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
