import { Shield } from "lucide-react";
import { useAuth } from "../auth/AuthContext";

export default function LoginPage() {
  const { login } = useAuth();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-lg border border-gray-200 p-10 max-w-md w-full text-center">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-primary rounded-xl">
            <Shield className="w-10 h-10 text-white" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-primary mb-2">Domain Review</h1>
        <p className="text-sm text-gray-500 mb-8">
          Sign in with your Microsoft 365 account to access domain health reports.
        </p>
        <button
          onClick={login}
          className="w-full flex items-center justify-center gap-3 px-6 py-3 bg-[#2f2f2f] text-white font-medium rounded-lg hover:bg-[#1a1a1a] transition-colors"
        >
          <svg className="w-5 h-5" viewBox="0 0 21 21" fill="none">
            <rect x="1" y="1" width="9" height="9" fill="#f25022" />
            <rect x="11" y="1" width="9" height="9" fill="#7fba00" />
            <rect x="1" y="11" width="9" height="9" fill="#00a4ef" />
            <rect x="11" y="11" width="9" height="9" fill="#ffb900" />
          </svg>
          Sign in with Microsoft
        </button>
      </div>
    </div>
  );
}
