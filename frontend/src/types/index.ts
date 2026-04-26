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
  | "ITERATING"
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
  time: string | null;
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
  daily_itinerary_json: string;
  total_estimated_budget: number;
  currency: string;
  match_reasoning: string;
  highlights: string;
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
  rankings_json: string;
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
  email_local: string;
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

export interface ApiError {
  detail: string;
}
