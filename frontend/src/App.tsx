import { useEffect } from "react";
import { Outlet, Routes, Route, useNavigate, useParams } from "react-router-dom";
import Layout from "@/components/Layout";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import TripDetailPage from "@/pages/TripDetailPage";
import TripPage from "@/pages/TripPage";
import JoinPage from "@/pages/JoinPage";

function LayoutWrapper() {
  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}

/** Redirect /join/:token → /trip/:token (for invitation email links) */
function JoinRedirect() {
  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  useEffect(() => {
    if (token) {
      navigate(`/trip/${token}`, { replace: true });
    }
  }, [token, navigate]);
  return null;
}

export default function App() {
  return (
    <Routes>
      {/* Login and landing render their own full-screen layouts */}
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<LandingPage />} />

      {/* All other routes wrapped in Layout */}
      <Route element={<LayoutWrapper />}>
        <Route path="/trip/:token" element={<TripPage />} />
        <Route path="/trip/:token/vote" element={<TripPage />} />
        <Route path="/join" element={<JoinPage />} />
        <Route path="/join/:token" element={<JoinRedirect />} />

        {/* Preview routes — no auth required, dev only */}
        <Route path="/preview/dashboard" element={<DashboardPage />} />
        <Route path="/preview/dashboard/trip" element={<TripDetailPage />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/trip/:tripId" element={<TripDetailPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
