const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

export type HealthLiveResponse = {
  status: "ok";
  service: string;
};

export type HealthReadyResponse = {
  status: "ready" | "degraded";
  checks: {
    database: "ok" | "error";
  };
};

export type ItineraryResponse = {
  id: string;
  title: string;
  destination: string;
  days: number;
  creator_user_id: string;
  status: string;
  visibility: string;
  cover_image_url: string | null;
  fork_source_itinerary_id: string | null;
  fork_source_author_nickname: string | null;
  fork_source_title: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicItineraryResponse = {
  id: string;
  title: string;
  destination: string;
  days: number;
  status: string;
  visibility: string;
  cover_image_url: string | null;
  author_nickname: string;
  forked_count: number;
  created_at: string;
  updated_at: string;
};

export type ForkItineraryResponse = {
  new_itinerary_id: string;
  title: string;
  source_itinerary_id: string;
  source_author_nickname: string;
  source_title: string;
};

export type ItineraryFieldDiff = {
  field: string;
  before: unknown;
  after: unknown;
};

export type ItineraryDiffResponse = {
  source_snapshot_id: string;
  source_itinerary_id: string;
  forked_itinerary_id: string;
  summary: {
    added: number;
    removed: number;
    modified: number;
  };
  metadata_diffs: ItineraryFieldDiff[];
  added_items: Array<{
    key: string;
    current: Record<string, unknown>;
  }>;
  removed_items: Array<{
    key: string;
    source: Record<string, unknown>;
  }>;
  modified_items: Array<{
    key: string;
    fields: ItineraryFieldDiff[];
  }>;
};

export type ItineraryListResponse = {
  items: ItineraryResponse[];
  total: number;
  offset: number;
  limit: number;
};

export type PublicItineraryListResponse = {
  items: PublicItineraryResponse[];
  total: number;
  offset: number;
  limit: number;
};

export type PoiResponse = {
  id: string;
  name: string;
  type: string;
  longitude: number;
  latitude: number;
  address: string | null;
  opening_hours: string | null;
  ticket_price: number | null;
  parent_poi_id: string | null;
  created_at: string;
  updated_at: string;
};


export type PoiListResponse = {
  items: PoiResponse[];
  total: number;
  offset: number;
  limit: number;
};

export type ItineraryItemPoiSnapshot = {
  id: string;
  name: string;
  type: string;
  longitude: number;
  latitude: number;
  address: string | null;
  opening_hours: string | null;
  ticket_price: number | null;
};

export type ItineraryItemWithPoi = {
  item_id: string;
  itinerary_id: string;
  day_index: number;
  sort_order: number;
  start_time: string | null;
  duration_minutes: number | null;
  cost: number | null;
  tips: string | null;
  poi: ItineraryItemPoiSnapshot;
};

export type ItineraryItemResponse = {
  id: string;
  itinerary_id: string;
  day_index: number;
  sort_order: number;
  poi_id: string;
  start_time: string | null;
  duration_minutes: number | null;
  cost: number | null;
  tips: string | null;
  created_at: string;
  updated_at: string;
};

export type ItineraryItemCreatePayload = {
  day_index: number;
  sort_order: number;
  poi_id: string;
  start_time: string | null;
  duration_minutes: number | null;
  cost: number | null;
  tips: string | null;
};

export type ItineraryItemUpdatePayload = Partial<ItineraryItemCreatePayload>;

export type ItineraryUpdatePayload = {
  title?: string;
  destination?: string;
  days?: number;
  status?: "draft" | "in_progress" | "published";
  visibility?: "private" | "public" | "followers";
  cover_image_url?: string | null;
};

export type ItineraryItemsWithPoiListResponse = {
  items: ItineraryItemWithPoi[];
};

export type AiPreviewPoi = {
  poi_id: string | null;
  name: string;
  type: string;
  longitude: number | null;
  latitude: number | null;
  address: string | null;
  opening_hours: string | null;
  ticket_price: number | null;
  match_source: "local" | "amap" | "unresolved";
};

export type AiPreviewItem = {
  day_index: number;
  sort_order: number;
  start_time: string | null;
  duration_minutes: number | null;
  cost: number | null;
  tips: string | null;
  poi: AiPreviewPoi;
};

export type AiPreviewRequest = {
  raw_text: string;
  itinerary_id: string;
};

export type AiPreviewResponse = {
  title: string;
  destination: string;
  days: number;
  items: AiPreviewItem[];
};

export type AiPreviewValidationErrorPayload = {
  error_code: string;
  reason: string;
  raw_excerpt: string | null;
  suggested_actions: string[];
};

export class AiPreviewValidationError extends Error {
  status: number;
  payload: AiPreviewValidationErrorPayload;

  constructor(message: string, status: number, payload: AiPreviewValidationErrorPayload) {
    super(message);
    this.name = "AiPreviewValidationError";
    this.status = status;
    this.payload = payload;
  }
}

function tryParseJson(text: string): unknown {
  if (!text.trim()) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function parseAiPreviewValidationPayload(raw: unknown): AiPreviewValidationErrorPayload | null {
  if (!raw || typeof raw !== "object") {
    return null;
  }
  const body = raw as { detail?: unknown };
  const detail = body.detail;
  if (!detail || typeof detail !== "object" || Array.isArray(detail)) {
    return null;
  }
  const d = detail as Record<string, unknown>;
  if (typeof d.error_code !== "string" || typeof d.reason !== "string") {
    return null;
  }
  return {
    error_code: d.error_code,
    reason: d.reason,
    raw_excerpt: typeof d.raw_excerpt === "string" ? d.raw_excerpt : null,
    suggested_actions: Array.isArray(d.suggested_actions)
      ? d.suggested_actions.filter((item): item is string => typeof item === "string")
      : []
  };
}

export function isAiPreviewValidationError(error: unknown): error is AiPreviewValidationError {
  if (!error || typeof error !== "object") {
    return false;
  }
  const candidate = error as { name?: unknown; status?: unknown; payload?: unknown };
  const payload = parseAiPreviewValidationPayload({ detail: candidate.payload });
  return candidate.name === "AiPreviewValidationError" && candidate.status === 422 && payload !== null;
}

export type AiImportRequest = {
  itinerary_id: string;
  preview: AiPreviewResponse;
};

export type AiImportResponse = {
  imported_count: number;
};

async function parseJsonResponse<T>(response: Response, requestLabel: string): Promise<T> {
  const contentType = response.headers.get("content-type") || "";
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`${requestLabel} failed with ${response.status}. Response: ${text.slice(0, 120)}`);
  }
  if (!contentType.includes("application/json")) {
    const text = await response.text();
    throw new Error(
      `${requestLabel} expected JSON but got "${contentType || "unknown"}". Response: ${text.slice(0, 120)}`
    );
  }
  return (await response.json()) as T;
}

function authHeaders(token?: string): HeadersInit {
  if (!token) {
    return {};
  }
  return {
    Authorization: `Bearer ${token}`
  };
}

export async function fetchLiveHealth(): Promise<HealthLiveResponse> {
  const response = await fetch(`${API_BASE_URL}/health/live`);
  return parseJsonResponse<HealthLiveResponse>(response, "Live health request");
}

export async function fetchReadyHealth(): Promise<HealthReadyResponse> {
  const response = await fetch(`${API_BASE_URL}/health/ready`);
  return parseJsonResponse<HealthReadyResponse>(response, "Ready health request");
}

export async function fetchItineraries(token: string): Promise<ItineraryListResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<ItineraryListResponse>(response, "List itineraries request");
}

export async function updateItinerary(
  itineraryId: string,
  payload: ItineraryUpdatePayload,
  token: string
): Promise<ItineraryResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<ItineraryResponse>(response, "Update itinerary request");
}

export async function deleteItinerary(itineraryId: string, token: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}`, {
    method: "DELETE",
    headers: authHeaders(token)
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Delete itinerary request failed with ${response.status}. Response: ${text.slice(0, 120)}`);
  }
}

export async function fetchPois(token: string | undefined, offset = 0, limit = 100): Promise<PoiListResponse> {
  const response = await fetch(`${API_BASE_URL}/pois?offset=${offset}&limit=${limit}`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<PoiListResponse>(response, "List scenic spots request");
}

export async function fetchItineraryItemsWithPoi(
  itineraryId: string,
  token: string
): Promise<ItineraryItemsWithPoiListResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<ItineraryItemsWithPoiListResponse>(response, "List itinerary items request");
}

export async function fetchPublicItineraries(offset = 0, limit = 20): Promise<PublicItineraryListResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries?offset=${offset}&limit=${limit}`);
  return parseJsonResponse<PublicItineraryListResponse>(response, "List public itineraries request");
}

export async function fetchPublicItinerary(itineraryId: string): Promise<PublicItineraryResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries/${itineraryId}`);
  return parseJsonResponse<PublicItineraryResponse>(response, "Get public itinerary request");
}

export async function fetchPublicItineraryItemsWithPoi(
  itineraryId: string
): Promise<ItineraryItemsWithPoiListResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries/${itineraryId}/items`);
  return parseJsonResponse<ItineraryItemsWithPoiListResponse>(response, "List public itinerary items request");
}

export async function forkPublicItinerary(itineraryId: string, token: string): Promise<ForkItineraryResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries/${itineraryId}/fork`, {
    method: "POST",
    headers: authHeaders(token)
  });
  return parseJsonResponse<ForkItineraryResponse>(response, "Fork public itinerary request");
}

export async function fetchItineraryDiff(itineraryId: string, token: string): Promise<ItineraryDiffResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/diff`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<ItineraryDiffResponse>(response, "Fetch itinerary diff request");
}

export async function createItineraryItem(
  itineraryId: string,
  payload: ItineraryItemCreatePayload,
  token: string
): Promise<ItineraryItemResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<ItineraryItemResponse>(response, "Create itinerary item request");
}

export async function updateItineraryItem(
  itineraryId: string,
  itemId: string,
  payload: ItineraryItemUpdatePayload,
  token: string
): Promise<ItineraryItemResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items/${itemId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<ItineraryItemResponse>(response, "Update itinerary item request");
}

export async function deleteItineraryItem(itineraryId: string, itemId: string, token: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(token)
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Delete itinerary item request failed with ${response.status}. Response: ${text.slice(0, 120)}`
    );
  }
}

export async function previewAiPlan(payload: AiPreviewRequest, token: string): Promise<AiPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/ai/preview`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify(payload)
  });
  if (response.status === 422) {
    const text = await response.text();
    const payload = parseAiPreviewValidationPayload(tryParseJson(text));
    if (payload) {
      throw new AiPreviewValidationError(payload.reason, 422, payload);
    }
    throw new Error(`Preview AI plan request failed with 422. Response: ${text.slice(0, 400)}`);
  }
  return parseJsonResponse<AiPreviewResponse>(response, "Preview AI plan request");
}

export async function importAiPlan(payload: AiImportRequest, token: string): Promise<AiImportResponse> {
  const response = await fetch(`${API_BASE_URL}/ai/import`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<AiImportResponse>(response, "Import AI plan request");
}

