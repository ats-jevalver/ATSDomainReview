import type { ReactNode } from "react";
import { NavLink } from "react-router-dom";
import { LayoutDashboard, Settings, Shield } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

interface LayoutProps {
  children: ReactNode;
}

export default function Layout({ children }: LayoutProps) {
  const { user, logout, ssoEnabled } = useAuth();
  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
      isActive
        ? "bg-white/15 text-white"
        : "text-blue-100 hover:bg-white/10 hover:text-white"
    }`;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Top navigation */}
      <nav className="bg-primary text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Brand */}
            <NavLink to="/" className="flex items-center gap-3">
              <Shield className="w-7 h-7 text-blue-300" />
              <span className="text-lg font-bold tracking-tight">
                Domain Review
              </span>
            </NavLink>

            {/* Nav links */}
            <div className="flex items-center gap-2">
              <NavLink to="/" end className={linkClass}>
                <LayoutDashboard className="w-4 h-4" />
                Dashboard
              </NavLink>
              <NavLink to="/settings" className={linkClass}>
                <Settings className="w-4 h-4" />
                Settings
              </NavLink>
              {ssoEnabled && user && (
                <div className="flex items-center gap-3 ml-4 pl-4 border-l border-white/20">
                  <div className="text-sm">
                    <div className="font-medium text-white">{user.name}</div>
                    {user.title && <div className="text-blue-200 text-xs">{user.title}</div>}
                  </div>
                  <button
                    onClick={logout}
                    className="text-xs text-blue-200 hover:text-white transition-colors"
                  >
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </nav>

      {/* Main content */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-gray-100 border-t border-gray-200 py-4 text-center text-xs text-gray-500">
        ATS Domain Review &mdash; Confidential Security Assessment Tool
      </footer>
    </div>
  );
}
