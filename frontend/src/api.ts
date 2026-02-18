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
  created_at: string;
  updated_at: string;
};

export type ItineraryListResponse = {
  items: ItineraryResponse[];
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

export type ItineraryItemsWithPoiListResponse = {
  items: ItineraryItemWithPoi[];
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

