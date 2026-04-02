import { Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Dashboard from "./components/Dashboard";
import ScanProgress from "./components/ScanProgress";
import ReportView from "./components/ReportView";
import BrandingSettings from "./components/BrandingSettings";
import LoginPage from "./components/LoginPage";
import { useAuth } from "./auth/AuthContext";

export default function App() {
  const { user, loading, ssoEnabled } = useAuth();

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-accent border-t-transparent rounded-full" />
      </div>
    );
  }

  if (ssoEnabled && !user) {
    return <LoginPage />;
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/scan/:scanId" element={<ScanProgress />} />
        <Route
          path="/scan/:scanId/report/:domain"
          element={<ReportView />}
        />
        <Route path="/settings" element={<BrandingSettings />} />
      </Routes>
    </Layout>
  );
}
