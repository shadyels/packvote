import type {
  Itinerary,
  Participant,
  ParticipantAccessResponse,
  ParticipantTripView,
  Preference,
  TokenResponse,
  Trip,
  TripSummary,
  User,
  Vote,
  VotingResults,
} from "@/types";

const BASE_URL: string = (import.meta.env.VITE_API_URL as string | undefined) ?? "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem("access_token");
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (!res.ok) {
    const body = (await res.json().catch(() => ({ detail: res.statusText }))) as {
      detail: string;
    };
    throw new ApiError(res.status, body.detail);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// Auth
export const auth = {
  register: (email: string, password: string, full_name?: string) =>
    request<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<User>("/auth/me"),
};

// Trips
export const trips = {
  list: () => request<TripSummary[]>("/trips/"),

  get: (tripId: number) => request<Trip>(`/trips/${tripId.toString()}`),

  create: (payload: {
    title: string;
    destination?: string;
    proposed_start_date?: string;
    proposed_end_date?: string;
    num_options: number;
    participant_emails: string[];
    notes?: string;
  }) =>
    request<Trip>("/trips/", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  triggerGeneration: (tripId: number) =>
    request<{ message: string }>(`/trips/${tripId.toString()}/generate`, { method: "POST" }),

  triggerNewIteration: (tripId: number) =>
    request<{ message: string }>(`/trips/${tripId.toString()}/new-iteration`, { method: "POST" }),

  pickWinner: (tripId: number, itineraryId: number) =>
    request<{ message: string }>(
      `/trips/${tripId.toString()}/pick-winner`,
      { method: "POST", body: JSON.stringify({ itinerary_id: itineraryId }) }
    ),

  update: (
    tripId: number,
    payload: {
      title?: string;
      destination?: string;
      proposed_start_date?: string;
      proposed_end_date?: string;
      num_options?: number;
      notes?: string;
    }
  ) =>
    request<Trip>(`/trips/${tripId.toString()}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  delete: (tripId: number) =>
    request<void>(`/trips/${tripId.toString()}`, { method: "DELETE" }),
};

// Participants
export const participants = {
  getByToken: (token: string) => request<Participant>(`/participants/${token}`),

  accessByCode: (trip_code: string, pin: string) =>
    request<ParticipantAccessResponse>("/participants/access-by-code", {
      method: "POST",
      body: JSON.stringify({ trip_code, pin }),
    }),

  getTripView: (token: string) =>
    request<ParticipantTripView>(`/participants/${token}/trip-view`),

  submitPreferences: (
    token: string,
    payload: {
      name?: string;
      preferred_start_date?: string;
      preferred_end_date?: string;
      budget_min?: number;
      budget_max?: number;
      currency?: string;
      interests?: string;
      activity_tags?: string[];
    }
  ) =>
    request<Preference>(`/participants/${token}/preferences`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  listByTrip: (tripId: number) =>
    request<Participant[]>(`/trips/${tripId.toString()}/participants`),
};

// Votes
export const votes = {
  submit: (tripId: number, token: string, rankings: number[]) =>
    request<Vote>(`/votes/trips/${tripId.toString()}/vote/${token}`, {
      method: "POST",
      body: JSON.stringify({ rankings }),
    }),

  adminVote: (tripId: number, rankings: number[]) =>
    request<Vote>(`/votes/trips/${tripId.toString()}/admin-vote`, {
      method: "POST",
      body: JSON.stringify({ rankings }),
    }),

  getResults: (tripId: number, iteration?: number) => {
    const qs = iteration !== undefined ? `?iteration=${iteration.toString()}` : "";
    return request<VotingResults>(`/votes/trips/${tripId.toString()}/results${qs}`);
  },
};

// Itineraries
export const itineraries = {
  getByTrip: (tripId: number) =>
    request<Itinerary[]>(`/trips/${tripId.toString()}/itineraries`),
};

export { ApiError };
