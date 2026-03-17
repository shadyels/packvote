import { useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { MapPin, Users, Vote, Sparkles, ChevronRight } from "lucide-react";
import Footer from "@/components/Footer";

const HERO_IMAGES = [
  { src: "/images/hero/javier-allegue-barros-i5Kx0P8A0d4-unsplash.jpg", photographer: "Javier Allegue Barros" },
  { src: "/images/hero/austin-ramsey-ghZlDMUcJ-8-unsplash.jpg", photographer: "Austin Ramsey" },
  { src: "/images/hero/eddy-billard-JOoOPt8tTPY-unsplash.jpg", photographer: "Eddy Billard" },
  { src: "/images/hero/alexandre-barbosa-cj7zHNRqp4w-unsplash.jpg", photographer: "Alexandre Barbosa" },
  { src: "/images/hero/nils-nedel-ONpGBpns3cs-unsplash.jpg", photographer: "Nils Nedel" },
  { src: "/images/hero/ian-ZMGUdXdwkHE-unsplash.jpg", photographer: "Ian" },
  { src: "/images/hero/chang-duong-Sj0iMtq_Z4w-unsplash.jpg", photographer: "Chang Duong" },
  { src: "/images/hero/milind-bedwa-15rk4yFjwHk-unsplash.jpg", photographer: "Milind Bedwa" },
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
    return () => { observer.disconnect(); };
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
        inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-6"
      }`}
      style={{ transitionDelay: delay }}
    >
      <div className="relative mb-5">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-black text-white shadow-sm">
          <Icon className="h-6 w-6" />
        </div>
        <span className="absolute -top-2 -right-2 flex h-5 w-5 items-center justify-center rounded-full bg-brand text-[10px] font-bold text-white">
          {number}
        </span>
      </div>
      <h3 className="mb-2 text-lg font-semibold text-black">{title}</h3>
      <p className="text-sm leading-relaxed text-black/55 max-w-xs">{description}</p>
    </div>
  );
}

function FeatureBlock({
  title,
  description,
  bullets,
  reverse,
}: {
  title: string;
  description: string;
  bullets: string[];
  reverse?: boolean;
}) {
  const { ref, inView } = useInView();
  return (
    <div
      ref={ref}
      className={`flex flex-col gap-8 md:flex-row md:items-center transition-all duration-700 ${
        reverse ? "md:flex-row-reverse" : ""
      } ${inView ? "opacity-100 translate-y-0" : "opacity-0 translate-y-8"}`}
    >
      {/* Text */}
      <div className="flex-1 space-y-4">
        <h3 className="text-2xl font-bold text-black md:text-3xl">{title}</h3>
        <p className="text-black/60 leading-relaxed">{description}</p>
        <ul className="space-y-2">
          {bullets.map((b) => (
            <li key={b} className="flex items-start gap-2 text-sm text-black/70">
              <span className="mt-0.5 h-4 w-4 shrink-0 rounded-full bg-brand/15 flex items-center justify-center">
                <span className="h-1.5 w-1.5 rounded-full bg-brand" />
              </span>
              {b}
            </li>
          ))}
        </ul>
      </div>

      {/* Visual card */}
      <div className="flex-1">
        <div className="rounded-2xl border border-border bg-card p-6 shadow-sm">
          <div className="space-y-3">
            {bullets.map((b, i) => (
              <div key={b} className="flex items-center gap-3">
                <div
                  className="h-8 w-8 rounded-lg flex items-center justify-center text-xs font-bold text-white"
                  style={{
                    background: i === 0 ? "#FF6B2C" : i === 1 ? "#1a2a4a" : "#2d6a4f",
                  }}
                >
                  {i + 1}
                </div>
                <div className="h-2 flex-1 rounded-full bg-muted overflow-hidden">
                  <div
                    className="h-full rounded-full bg-brand/60 transition-all"
                    style={{ width: `${String(90 - i * 18)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* ─── Standalone nav (transparent over hero) ─── */}
      <header className="absolute top-0 left-0 right-0 z-50 px-4 py-5">
        <nav className="mx-auto flex max-w-6xl items-center justify-between">
          <span className="text-xl font-bold text-white drop-shadow-sm">
            PackVote
          </span>
          <div className="flex items-center gap-3">
            <Link
              to="/join"
              className="rounded-md px-3 py-1.5 text-sm font-medium text-white/90 hover:text-white transition-colors"
            >
              Join a Trip
            </Link>
            <Link
              to="/login"
              className="rounded-md bg-white/15 border border-white/30 backdrop-blur-sm px-3 py-1.5 text-sm font-medium text-white hover:bg-white/25 transition-colors"
            >
              Sign In
            </Link>
          </div>
        </nav>
      </header>

      {/* ─── Hero ─── */}
      <section className="relative flex min-h-[85vh] items-center justify-center overflow-hidden">
        {/* Background photo */}
        <img
          src={heroImage.src}
          alt=""
          className="absolute inset-0 h-full w-full object-cover"
        />
        {/* Dark overlay so text stays readable */}
        <div className="absolute inset-0 bg-black/50" />
        {/* Attribution */}
        <a
          href="https://unsplash.com"
          target="_blank"
          rel="noopener noreferrer"
          className="absolute bottom-28 right-4 z-10 text-[10px] text-white/40 hover:text-white/60 transition-colors"
        >
          Photo: {heroImage.photographer} / Unsplash
        </a>

        {/* Content */}
        <div className="relative z-10 mx-auto max-w-4xl px-4 text-center">
          <div
            className="mb-4 inline-flex items-center gap-1.5 rounded-full border border-white/20 bg-white/10 px-3 py-1 text-xs font-medium text-white/80 backdrop-blur-sm animate-fade-in"
          >
            <Sparkles className="h-3 w-3 text-brand" />
            AI-powered group travel planning
          </div>

          <h1
            className="mb-6 text-5xl font-bold leading-tight tracking-tight text-white md:text-7xl animate-fade-in-up"
            style={{ animationDelay: "100ms", opacity: 0, animationFillMode: "forwards" }}
          >
            Every trip,{" "}
            <span className="text-brand">decided together.</span>
          </h1>

          <p
            className="mx-auto mb-10 max-w-xl text-lg text-white/70 leading-relaxed animate-fade-in-up"
            style={{ animationDelay: "250ms", opacity: 0, animationFillMode: "forwards" }}
          >
            Collect everyone's preferences, let AI generate personalized destinations,
            then vote as a group — no endless group chats required.
          </p>

          <div
            className="flex flex-col items-center gap-3 sm:flex-row sm:justify-center animate-fade-in-up"
            style={{ animationDelay: "400ms", opacity: 0, animationFillMode: "forwards" }}
          >
            <Link
              to="/login"
              className="inline-flex items-center gap-2 rounded-lg bg-brand px-6 py-3 text-sm font-semibold text-white shadow-lg hover:bg-brand-hover transition-all duration-150 hover:shadow-xl hover:-translate-y-0.5"
            >
              Create a Trip
              <ChevronRight className="h-4 w-4" />
            </Link>
            <Link
              to="/join"
              className="inline-flex items-center gap-2 rounded-lg border border-white/30 bg-white/10 px-6 py-3 text-sm font-semibold text-white backdrop-blur-sm hover:bg-white/20 transition-all duration-150"
            >
              Join a Trip
            </Link>
          </div>
        </div>

        {/* Bottom fade */}
        <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-background to-transparent" />
      </section>

      {/* ─── How It Works ─── */}
      <section className="py-20 md:py-32 px-4">
        <div className="mx-auto max-w-6xl">
          <div className="mb-14 text-center">
            <h2 className="text-3xl font-bold text-black md:text-4xl">
              From idea to itinerary
            </h2>
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
      <section className="py-20 md:py-32 px-4 bg-card border-y border-border">
        <div className="mx-auto max-w-6xl space-y-20">
          <FeatureBlock
            title="AI that reads the room"
            description="PackVote's AI weighs everyone's stated preferences — budgets, travel style, dietary needs — and generates destinations that genuinely fit the whole group, not just the loudest voice."
            bullets={[
              "Personalized destination recommendations",
              "Full day-by-day itineraries with activities",
              "Budget breakdowns per person",
            ]}
          />
          <FeatureBlock
            title="Voting that's actually fair"
            description="Ranked-choice voting eliminates the 'two equal options, group splits' problem. Everyone ranks all options; the math picks the true group favorite."
            bullets={[
              "Instant-runoff ranked-choice algorithm",
              "Re-vote rounds if no majority",
              "Trip creator can finalize at any time",
            ]}
            reverse
          />
        </div>
      </section>

      {/* ─── Bottom CTA ─── */}
      <section className="relative py-24 md:py-36 px-4 overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            background: "linear-gradient(145deg, #1a2a1a 0%, #2d4a3e 40%, #1a3a5c 100%)",
          }}
        />
        <div className="absolute inset-0 opacity-15"
          style={{
            backgroundImage: "radial-gradient(ellipse at 70% 60%, rgba(255,107,44,0.4) 0%, transparent 55%)",
          }}
        />

        <div className="relative z-10 mx-auto max-w-2xl text-center">
          <MapPin className="mx-auto mb-5 h-10 w-10 text-brand" />
          <h2 className="mb-4 text-4xl font-bold text-white md:text-5xl">
            Ready to plan?
          </h2>
          <p className="mb-8 text-white/65 text-lg">
            Start a trip in under a minute — your group handles the rest.
          </p>
          <Link
            to="/login"
            className="inline-flex items-center gap-2 rounded-lg bg-brand px-8 py-3.5 text-sm font-semibold text-white shadow-lg hover:bg-brand-hover transition-all duration-150 hover:shadow-xl hover:-translate-y-0.5"
          >
            Create a Trip
            <ChevronRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="absolute bottom-0 left-0 right-0 h-20 bg-gradient-to-t from-background to-transparent" />
      </section>

      <Footer />
    </div>
  );
}
