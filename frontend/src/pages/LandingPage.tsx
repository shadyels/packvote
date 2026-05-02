import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import {
  MapPin,
  Users,
  Vote,
  Sparkles,
  ChevronRight,
  Star,
  Utensils,
  Compass,
  Trophy,
  CheckCircle2,
} from "lucide-react";
import Footer from "@/components/Footer";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const HERO_IMAGES = [
  { src: "/images/hero/javier-allegue-barros-i5Kx0P8A0d4-unsplash.jpg" },
  { src: "/images/hero/austin-ramsey-ghZlDMUcJ-8-unsplash.jpg" },
  { src: "/images/hero/eddy-billard-JOoOPt8tTPY-unsplash.jpg" },
  { src: "/images/hero/alexandre-barbosa-cj7zHNRqp4w-unsplash.jpg" },
  { src: "/images/hero/nils-nedel-ONpGBpns3cs-unsplash.jpg" },
  { src: "/images/hero/ian-ZMGUdXdwkHE-unsplash.jpg" },
  { src: "/images/hero/chang-duong-Sj0iMtq_Z4w-unsplash.jpg" },
  { src: "/images/hero/milind-bedwa-15rk4yFjwHk-unsplash.jpg" },
];

const heroImage = HERO_IMAGES[Math.floor(Math.random() * HERO_IMAGES.length)];

// Intersection Observer hook for scroll-triggered animations
function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold }
    );
    observer.observe(el);
    return () => {
      observer.disconnect();
    };
  }, [threshold]);

  return { ref, inView };
}

function HowItWorksStep({
  number,
  icon: Icon,
  title,
  description,
  delay,
}: {
  number: string;
  icon: React.ElementType;
  title: string;
  description: string;
  delay: string;
}) {
  const { ref, inView } = useInView();
  return (
    <div
      ref={ref}
      className={`flex flex-col items-center text-center transition-all duration-700 ${
        inView ? "translate-y-0 opacity-100" : "translate-y-6 opacity-0"
      }`}
      style={{ transitionDelay: delay }}
    >
      <div className="relative mb-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-black text-white shadow-sm">
          <Icon className="h-6 w-6" />
        </div>
        <span className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-brand text-[10px] font-bold text-white">
          {number}
        </span>
      </div>
      <h3 className="mb-2 text-lg font-semibold text-black">{title}</h3>
      <p className="max-w-xs text-sm leading-relaxed text-black/55">{description}</p>
    </div>
  );
}

function AIRecommendationVisual() {
  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-card shadow-sm">
      {/* Gradient header */}
      <div
        className="px-5 py-4"
        style={{ background: "linear-gradient(135deg, #FF6B2C 0%, #e8522a 60%, #c94b2a 100%)" }}
      >
        <div className="flex items-center justify-between">
          <span className="text-xs font-semibold uppercase tracking-wider text-white/70">
            AI Recommendation
          </span>
          <div className="flex items-center gap-1 text-white/90">
            <Star className="h-3.5 w-3.5 fill-white/80 text-white/80" />
            <span className="text-xs font-bold">94% match</span>
          </div>
        </div>
        <p className="mt-1 text-lg font-bold text-white">Lisbon, Portugal</p>
        <p className="mt-0.5 text-xs text-white/60">~$1,100 per person · 7 days</p>
      </div>

      {/* Body */}
      <div className="space-y-4 px-5 py-4">
        <div className="flex flex-wrap gap-1.5">
          <Badge variant="secondary">
            <Utensils className="mr-1 h-3 w-3" />
            Food scene
          </Badge>
          <Badge variant="secondary">
            <Compass className="mr-1 h-3 w-3" />
            Walkable
          </Badge>
          <Badge variant="secondary">Budget-friendly</Badge>
        </div>

        <div>
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-black/40">
            Day 1 Preview
          </p>
          <div className="space-y-1.5">
            {[
              { time: "9:00 AM", activity: "Alfama district morning walk" },
              { time: "1:00 PM", activity: "Mercado da Ribeira lunch" },
              { time: "4:00 PM", activity: "Belém Tower & pastéis" },
            ].map(({ time, activity }) => (
              <div key={time} className="flex items-center gap-2 text-xs text-black/65">
                <span className="w-14 shrink-0 font-medium text-black/40">{time}</span>
                <span>{activity}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function RankedVotingVisual() {
  const options = [
    { rank: 1, name: "Lisbon, Portugal", votes: 8, pct: 73, winner: true },
    { rank: 2, name: "Porto, Portugal", votes: 5, pct: 45, winner: false },
    { rank: 3, name: "Seville, Spain", votes: 2, pct: 18, winner: false },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Round 2 Results</CardTitle>
          <Badge variant="outline" className="text-xs font-normal">
            Instant Runoff
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {options.map((opt) => (
          <div key={opt.name} className="space-y-1">
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-black/30">#{opt.rank}</span>
                <span className={opt.winner ? "font-semibold text-black" : "text-black/60"}>
                  {opt.name}
                </span>
              </div>
              <span className="text-xs text-black/40">{opt.votes} votes</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-muted">
              <div
                className={`h-full rounded-full transition-all ${opt.winner ? "bg-brand" : "bg-black/15"}`}
                style={{ width: `${String(opt.pct)}%` }}
              />
            </div>
          </div>
        ))}

        <div className="bg-brand/8 mt-4 flex items-center gap-2 rounded-xl px-3 py-2.5">
          <CheckCircle2 className="h-4 w-4 shrink-0 text-brand" />
          <div>
            <p className="text-xs font-semibold text-brand">Winner: Lisbon, Portugal</p>
            <p className="text-[11px] text-black/45">73% majority · group decision finalized</p>
          </div>
          <Trophy className="ml-auto h-4 w-4 text-brand/50" />
        </div>
      </CardContent>
    </Card>
  );
}

function FeatureBlock({
  title,
  description,
  bullets,
  visual,
  reverse,
}: {
  title: string;
  description: string;
  bullets: string[];
  visual: React.ReactNode;
  reverse?: boolean;
}) {
  const { ref, inView } = useInView();
  return (
    <div
      ref={ref}
      className={`flex flex-col gap-8 transition-all duration-700 md:flex-row md:items-center ${
        reverse ? "md:flex-row-reverse" : ""
      } ${inView ? "translate-y-0 opacity-100" : "translate-y-8 opacity-0"}`}
    >
      {/* Text */}
      <div className="flex-1 space-y-4">
        <h3 className="text-2xl font-bold text-black md:text-3xl">{title}</h3>
        <p className="leading-relaxed text-black/60">{description}</p>
        <ul className="space-y-2">
          {bullets.map((b) => (
            <li key={b} className="flex items-start gap-2 text-sm text-black/70">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-brand/15">
                <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              </span>
              {b}
            </li>
          ))}
        </ul>
      </div>

      {/* Visual */}
      <div className="flex-1">{visual}</div>
    </div>
  );
}

export default function LandingPage() {
  const { isAuthenticated, logout } = useAuth();
  const navigate = useNavigate();
  const handleLogout = () => {
    logout();
    navigate("/");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* ─── Standalone nav (transparent over hero) ─── */}
      <header className="absolute left-0 right-0 top-0 z-50 px-4 py-5">
        <nav className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="text-xl font-bold text-white drop-shadow-sm">PackVote</span>
          <div className="flex items-center gap-3">
            {isAuthenticated ? (
              <>
                <Link
                  to="/dashboard"
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-white/90 transition-colors hover:text-white"
                >
                  Dashboard
                </Link>
                <button
                  onClick={handleLogout}
                  className="rounded-md border border-white/30 bg-white/15 px-3 py-1.5 text-sm font-medium text-white backdrop-blur-sm transition-colors hover:bg-white/25"
                >
                  Logout
                </button>
              </>
            ) : (
              <>
                <Link
                  to="/join"
                  className="rounded-md px-3 py-1.5 text-sm font-medium text-white/90 transition-colors hover:text-white"
                >
                  Join a Trip
                </Link>
                <Link
                  to="/login"
                  className="rounded-md border border-white/30 bg-white/15 px-3 py-1.5 text-sm font-medium text-white backdrop-blur-sm transition-colors hover:bg-white/25"
                >
                  Sign In
                </Link>
              </>
            )}
          </div>
        </nav>
      </header>

      {/* ─── Hero ─── */}
      <section className="relative flex min-h-screen min-h-[100svh] items-center justify-center overflow-hidden md:min-h-[85vh]">
        {/* Background photo */}
        <img src={heroImage.src} alt="" className="absolute inset-0 h-full w-full object-cover" />
        {/* Vignette overlay — lighter at edges, denser in the middle */}
        <div
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(ellipse at 50% 50%, rgba(0,0,0,0.58) 0%, rgba(0,0,0,0.38) 45%, rgba(0,0,0,0.22) 100%)",
          }}
        />
        {/* Content */}
        <div className="relative z-10 mx-auto max-w-4xl px-4 text-center">
          <div className="animate-fade-in mb-4 inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white/80 backdrop-blur-sm">
            <Sparkles className="h-3 w-3 text-brand" />
            AI-powered group travel planning
          </div>

          <h1
            className="animate-fade-in-up mb-6 text-5xl font-bold leading-tight tracking-tight text-white md:text-7xl"
            style={{ animationDelay: "100ms", opacity: 0, animationFillMode: "forwards" }}
          >
            Every trip, <span className="text-brand">decided together.</span>
          </h1>

          <p
            className="animate-fade-in-up mx-auto mb-10 max-w-xl text-lg leading-relaxed text-white/70"
            style={{ animationDelay: "250ms", opacity: 0, animationFillMode: "forwards" }}
          >
            Collect everyone's preferences, let AI generate personalized destinations, then vote as
            a group. No endless group chats required.
          </p>

          <div
            className="animate-fade-in-up flex flex-col items-center gap-3 sm:flex-row sm:justify-center"
            style={{ animationDelay: "400ms", opacity: 0, animationFillMode: "forwards" }}
          >
            <Link
              to={isAuthenticated ? "/dashboard" : "/login"}
              className="inline-flex items-center gap-2 rounded-lg bg-brand px-6 py-3 text-sm font-semibold text-white shadow-lg transition-all duration-150 hover:-translate-y-0.5 hover:bg-brand-hover hover:shadow-xl"
            >
              Create a Trip
              <ChevronRight className="h-4 w-4" />
            </Link>
            {!isAuthenticated && (
              <Link
                to="/join"
                className="inline-flex items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-6 py-3 text-sm font-semibold text-white backdrop-blur-sm transition-all duration-150 hover:bg-white/20"
              >
                Join a Trip
              </Link>
            )}
          </div>
        </div>

        {/* Bottom fade */}
        <div
          className="absolute bottom-0 left-0 right-0 h-40"
          style={{
            background:
              "linear-gradient(to top, hsl(80,14%,97%) 7%, hsl(80,14%,97%,0.8) 30%, hsl(80,14%,97%,0.4) 60%, transparent 100%)",
          }}
        />
      </section>

      {/* ─── How It Works ─── */}
      <section className="px-4 py-20 md:py-32">
        <div className="mx-auto max-w-6xl">
          <div className="mb-14 text-center">
            <h2 className="text-3xl font-bold text-black md:text-4xl">From idea to itinerary</h2>
            <p className="mt-3 text-black/50">Three steps. Zero arguments.</p>
          </div>

          <div className="grid grid-cols-1 gap-10 md:grid-cols-3">
            <HowItWorksStep
              number="01"
              icon={Users}
              title="Create & invite"
              description="Create a trip, set your travel window, and invite your group by email. No accounts needed for participants."
              delay="0ms"
            />
            <HowItWorksStep
              number="02"
              icon={Sparkles}
              title="Collect preferences"
              description="Everyone submits their budget, travel style, and must-haves. The AI reads all of them at once."
              delay="120ms"
            />
            <HowItWorksStep
              number="03"
              icon={Vote}
              title="Vote on options"
              description="AI generates tailored destinations. Your group ranks them with instant-runoff voting — the best choice wins."
              delay="240ms"
            />
          </div>
        </div>
      </section>

      {/* ─── Feature highlights ─── */}
      <section className="px-4 py-20 md:py-32">
        <div className="mx-auto max-w-6xl">
          <div className="space-y-20 rounded-3xl border border-border bg-card px-8 py-16 md:px-14">
            <FeatureBlock
              title="AI that reads the room"
              description="PackVote's AI weighs everyone's stated preferences — budgets, travel style, dietary needs, and generates destinations that genuinely fit the whole group, not just the loudest voice."
              bullets={[
                "Personalized destination recommendations",
                "Full day-by-day itineraries with activities",
                "Budget breakdowns per person",
              ]}
              visual={<AIRecommendationVisual />}
            />
            <FeatureBlock
              title="Voting that's actually fair"
              description="Ranked-choice voting eliminates the 'two equal options, group splits' problem. Everyone ranks all options; the math picks the true group favorite."
              bullets={[
                "Instant-runoff ranked-choice algorithm",
                "Re-vote rounds if no majority",
                "Trip creator can finalize at any time",
              ]}
              visual={<RankedVotingVisual />}
              reverse
            />
          </div>
        </div>
      </section>

      {/* ─── Bottom CTA ─── */}
      <section className="relative overflow-hidden bg-[#192840] px-4 py-24 md:py-36">
        {/* Top fade — offwhite dissolving into the dark section */}
        <div
          className="absolute left-0 right-0 top-0 h-40"
          style={{
            background:
              "linear-gradient(to bottom, hsl(80,14%,97%) 0%, rgba(248,248,246,0.8) 20%, rgba(248,248,246,0.3) 70%, transparent 100%)",
          }}
        />

        {/* Content — centered in the dark area */}
        <div className="relative z-10 mx-auto max-w-2xl px-4 pt-12 text-center md:pt-36">
          <MapPin className="mx-auto mb-5 h-10 w-10 text-brand" />
          <h2 className="mb-4 text-4xl font-bold text-white md:text-5xl">Ready to plan?</h2>
          <p className="mb-8 text-lg text-white/65">
            Start a trip in under a minute. Your group handles the rest.
          </p>
          <Link
            to={isAuthenticated ? "/dashboard" : "/login"}
            className="inline-flex items-center gap-2 rounded-lg bg-brand px-8 py-3.5 text-sm font-semibold text-white shadow-lg transition-all duration-150 hover:-translate-y-0.5 hover:bg-brand-hover hover:shadow-xl"
          >
            Create a Trip
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  );
}
