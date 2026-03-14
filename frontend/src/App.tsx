import { Outlet, Routes, Route } from "react-router-dom";
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

export default function App() {
  return (
    <Routes>
      {/* Login renders its own full-screen layout */}
      <Route path="/login" element={<LoginPage />} />

      {/* All other routes wrapped in Layout */}
      <Route element={<LayoutWrapper />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/trip/:token" element={<TripPage />} />
        <Route path="/join" element={<JoinPage />} />

        {/* Protected routes */}
        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/dashboard/trip/:tripId" element={<TripDetailPage />} />
        </Route>
      </Route>
    </Routes>
  );
}
