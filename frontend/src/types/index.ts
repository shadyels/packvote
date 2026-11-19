export interface User {
  id: number;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface Trip {
  id: number;
  trip_code: string;
  creator_id: number;
  title: string;
  destination: string | null;
  proposed_start_date: string | null;
  proposed_end_date: string | null;
  num_options: number;
  status: TripStatus;
  current_iteration: number;
  max_iterations: number;
  winner_itinerary_id: number | null;
  generation_error: string | null;
  notes: string | null;
  created_at: string;
}

export type TripStatus =
  | "CREATED"
  | "COLLECTING_PREFERENCES"
  | "GENERATING"
  | "GENERATION_FAILED"
  | "VOTING"
  | "FINALIZED";

export interface TripSummary {
  id: number;
  trip_code: string;
  title: string;
  destination: string | null;
  status: TripStatus;
  participant_count: number;
  preferences_submitted_count: number;
  created_at: string;
}

export interface InvitedTripSummary extends TripSummary {
  participant_token: string;
}

export interface Participant {
  id: number;
  trip_id: number;
  email: string;
  name: string | null;
  preferences_submitted: boolean;
  has_voted_current_iteration: boolean;
  created_at: string;
}

export interface Preference {
  id: number;
  participant_id: number;
  trip_id: number;
  preferred_start_date: string | null;
  preferred_end_date: string | null;
  budget_min: number | null;
  budget_max: number | null;
  currency: string;
  interests: string | null;
  submitted_at: string;
}

export interface DailyActivity {
  time: "morning" | "afternoon" | "evening" | "night" | null;
  title: string;
  description: string;
  estimated_cost: number | null;
}

export interface DayItinerary {
  day_number: number;
  title: string;
  activities: DailyActivity[];
  estimated_cost: number | null;
}

export interface Itinerary {
  id: number;
  trip_id: number;
  iteration_number: number;
  option_title: string | null;
  destination_name: string;
  destination_description: string;
  daily_itinerary: DayItinerary[];
  total_estimated_budget: number;
  currency: string;
  match_reasoning: string;
  highlights: string[];
  model_used: string | null;
  provider: string | null;
  created_at: string;
  // Phase 2 price fields
  estimated_cost: number | null;
  price_last_updated: string | null;
  price_source: string | null;
}

export interface Vote {
  id: number;
  participant_id: number;
  trip_id: number;
  iteration_number: number;
  rankings: number[];
  submitted_at: string;
}

export interface VoteRoundResult {
  round_number: number;
  results: Record<number, number>;
  eliminated_option_id: number | null;
  winner_id: number | null;
}

export interface VotingResults {
  trip_id: number;
  iteration_number: number;
  rounds: VoteRoundResult[];
  winner_id: number | null;
  is_complete: boolean;
}

export interface TripPublicInfo {
  id: number;
  title: string;
  destination: string | null;
  proposed_start_date: string | null;
  proposed_end_date: string | null;
  status: TripStatus;
  num_options: number;
  current_iteration: number;
  winner_itinerary_id: number | null;
  generation_error: string | null;
  notes: string | null;
}

export interface ParticipantBrief {
  id: number;
  name: string | null;
  preferences_submitted: boolean;
}

export interface ParticipantTripView {
  participant: Participant;
  trip: TripPublicInfo;
  participants: ParticipantBrief[];
  itineraries: Itinerary[];
  voting_results: VotingResults | null;
  has_voted: boolean;
}

export interface ParticipantAccessResponse {
  token: string;
  participant: Participant;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface PlatformStats {
  generated_at: string;
  totals: {
    trips: number;
    users: number;
    participants: number;
    votes: number;
    itineraries: number;
    ai_attempts: number;
    tokens_in: number;
    tokens_out: number;
  };
  funnel: { status: TripStatus; trips: number }[];
  generation: {
    attempts: number;
    valid_attempts: number;
    valid_rate: number | null;
    runs: number;
    runs_succeeded: number;
    attempts_per_run: { attempts: number; runs: number }[];
    finish_reasons: { finish_reason: string | null; attempts: number }[];
    latency: {
      p50_ms: number | null;
      p95_ms: number | null;
      sample_size: number;
      histogram: { min_ms: number; max_ms: number | null; attempts: number }[];
    };
    orphaned_attempts: number;
  };
  by_model: {
    provider: string;
    model: string;
    attempts: number;
    valid_attempts: number;
    tokens_in: number;
    tokens_out: number;
  }[];
  by_prompt_version: {
    prompt_version: string | null;
    successful_generations: number;
    itineraries: number;
  }[];
  activity: { date: string; trips: number; tokens_in: number; tokens_out: number }[];
  voting: {
    avg_participants_per_trip: number | null;
    trips_reached_voting: number;
    avg_votes_per_trip: number | null;
    finalized_trips: number;
    iterations_to_finalize: { iterations: number; trips: number }[];
  };
  sampling: { row_cap: number; truncated: boolean };
}
