import { Routes, Route } from "react-router-dom";
import LandingPage from "@/pages/LandingPage";
import LoginPage from "@/pages/LoginPage";
import DashboardPage from "@/pages/DashboardPage";
import TripPage from "@/pages/TripPage";
import JoinPage from "@/pages/JoinPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/trip/:token" element={<TripPage />} />
      <Route path="/join" element={<JoinPage />} />
    </Routes>
  );
}
