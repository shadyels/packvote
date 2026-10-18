import { Navigate, Route, Routes, useParams } from "react-router-dom";
import AppShell from "@/components/AppShell";
import ProtectedRoute from "@/components/ProtectedRoute";
import Landing from "@/pages/Landing";
import Login from "@/pages/Login";
import ResetPassword from "@/pages/ResetPassword";
import Join from "@/pages/Join";
import Dashboard from "@/pages/Dashboard";
import TripDetail from "@/pages/TripDetail";
import Trip from "@/pages/Trip";
import NotFound from "@/pages/NotFound";

/** /join/:token (invitation email links) -> /trip/:token */
function JoinRedirect() {
  const { token = "" } = useParams<{ token: string }>();
  return <Navigate to={`/trip/${token}`} replace />;
}

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/reset-password" element={<ResetPassword />} />
        <Route path="/join" element={<Join />} />
        <Route path="/join/:token" element={<JoinRedirect />} />
        <Route path="/trip/:token" element={<Trip />} />
        <Route path="/trip/:token/vote" element={<Trip />} />

        <Route element={<ProtectedRoute />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/dashboard/trip/:tripId" element={<TripDetail />} />
        </Route>

        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}
