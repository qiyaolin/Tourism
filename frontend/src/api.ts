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
  start_date: string | null;
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
  last_visited_at: string | null;
  created_at: string;
  updated_at: string;
};

export type PublicItineraryShareMetaResponse = {
  itinerary_id: string;
  title: string;
  destination: string;
  days: number;
  author_nickname: string;
  description: string;
  cover_image_url: string | null;
  public_url: string;
  share_card_url: string;
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
  latest_source_snapshot_id: string | null;
  stale_warning: boolean;
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
  action_statuses: Record<string, string>;
};

export type ItineraryDiffActionType = "metadata" | "added" | "removed" | "modified";
export type ItineraryDiffActionName = "applied" | "rolled_back" | "ignored" | "read";

export type ItineraryDiffActionInput = {
  diff_key: string;
  diff_type: ItineraryDiffActionType;
  action: ItineraryDiffActionName;
  reason?: string | null;
};

export type ItineraryDiffActionBatchResponse = {
  applied_count: number;
  rolled_back_count: number;
  ignored_count: number;
  read_count: number;
  warnings: string[];
  action_statuses: Record<string, string>;
};

export type ItineraryDiffActionStatusResponse = {
  source_snapshot_id: string;
  items: Array<{
    diff_key: string;
    diff_type: string;
    action: string;
    reason: string | null;
    actor_user_id: string;
    created_at: string;
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

export type ExploreHeatPointResponse = {
  poi_id: string;
  name: string;
  longitude: number;
  latitude: number;
  heat_score: number;
};

export type ExploreHeatPointListResponse = {
  items: ExploreHeatPointResponse[];
};

export type ExploreRecommendationItemResponse = {
  itinerary: PublicItineraryResponse;
  score: number;
  reasons: string[];
};

export type ExploreRecommendationListResponse = {
  items: ExploreRecommendationItemResponse[];
};

export type ExploreVisitLogResponse = {
  itinerary_id: string;
  last_viewed_at: string;
  view_count: number;
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
  ticket_rules: PoiTicketRuleItem[];
  parent_poi_id: string | null;
  created_at: string;
  updated_at: string;
};

export type PricingAudienceItem = {
  code: string;
  label: string;
  sort_order: number;
};

export type PricingAudienceListResponse = {
  items: PricingAudienceItem[];
};

export type PoiTicketRuleItem = {
  id: string;
  audience_code: string;
  audience_label: string;
  ticket_type: string;
  time_slot: string;
  price: number;
  currency: string;
  conditions: string | null;
  is_active: boolean;
};

export type PoiTicketRuleUpsert = {
  id?: string;
  audience_code: string;
  ticket_type: string;
  time_slot: string;
  price: number;
  currency: string;
  conditions?: string | null;
  is_active?: boolean;
};

export type PoiTicketRuleListResponse = {
  items: PoiTicketRuleItem[];
};

export type PoiCorrectionType = {
  id: string;
  code: string;
  label: string;
  target_field: string;
  value_kind: string;
  placeholder: string | null;
  input_mode: "ticket_rules" | "time_range" | "text";
  input_schema: Record<string, unknown> | null;
  help_text: string | null;
  sort_order: number;
};

export type PoiCorrectionTypeListResponse = {
  items: PoiCorrectionType[];
};

export type PoiCorrectionResponse = {
  id: string;
  poi_id: string;
  territory_id: string | null;
  territory_name: string | null;
  source_poi_name_snapshot: string | null;
  source_itinerary_id: string | null;
  source_itinerary_title_snapshot: string | null;
  source_itinerary_author_snapshot: string | null;
  type_code: string;
  type_label: string;
  target_field: string;
  value_kind: string;
  proposed_value: string | null;
  details: string | null;
  photo_url: string | null;
  status: "pending" | "accepted" | "rejected";
  submitter_user_id: string;
  reviewer_user_id: string | null;
  review_comment: string | null;
  created_at: string;
  updated_at: string;
  reviewed_at: string | null;
};

export type PoiCorrectionListResponse = {
  items: PoiCorrectionResponse[];
  total: number;
  offset: number;
  limit: number;
};

export type BadgeDefResponse = {
  id: string;
  code: string;
  name: string;
  description: string;
  icon_url: string | null;
};

export type UserBadgeResponse = {
  id: string;
  badge_id: string;
  created_at: string;
  badge_def: BadgeDefResponse;
};

export type UserContributionResponse = {
  id: string;
  action_type: string;
  points: number;
  created_at: string;
  source_id: string | null;
};

export type PassportResponse = {
  user_id: string;
  total_points: number;
  level: number;
  badges: UserBadgeResponse[];
  recent_contributions: UserContributionResponse[];
};

export type TerritoryGuardianBrief = {
  user_id: string;
  nickname: string;
  state: "active" | "honorary" | "suspended";
  granted_at: string;
};

export type TerritoryRegionResponse = {
  id: string;
  code: string;
  name: string;
  status: "active" | "inactive";
  poi_count: number;
  boundary_wkt: string;
  centroid_wkt: string;
  guardians: TerritoryGuardianBrief[];
};

export type TerritoryRegionListResponse = {
  items: TerritoryRegionResponse[];
};

export type TerritoryGuardianApplicationResponse = {
  id: string;
  territory_id: string;
  territory_name: string;
  applicant_user_id: string;
  applicant_nickname: string;
  reason: string | null;
  status: "pending" | "approved" | "rejected";
  reviewer_user_id: string | null;
  reviewer_nickname: string | null;
  review_comment: string | null;
  reviewed_at: string | null;
  created_at: string;
};

export type TerritoryGuardianApplicationListResponse = {
  items: TerritoryGuardianApplicationResponse[];
  total: number;
  offset: number;
  limit: number;
};

export type TerritoryRebuildResponse = {
  generated_regions: number;
  assigned_pois: number;
  inactive_regions: number;
};

export type TerritoryGuardianCheckInResponse = {
  territory_id: string;
  guardian_user_id: string;
  checked_in_at: string;
};

export type TerritoryGuardianReputationItemResponse = {
  guardian_id: string;
  territory_id: string;
  territory_name: string;
  guardian_user_id: string;
  guardian_nickname: string;
  guardian_state: "active" | "honorary" | "suspended";
  reviewed_count: number;
  accepted_count: number;
  accuracy: number;
  threshold: number;
  status: "ok" | "suspended";
  calculated_at: string;
};

export type TerritoryGuardianReputationListResponse = {
  items: TerritoryGuardianReputationItemResponse[];
};


export type PoiCorrectionReviewResponse = {
  correction: PoiCorrectionResponse;
  poi_updated: boolean;
};

export type UserNotificationResponse = {
  id: string;
  recipient_user_id: string;
  sender_user_id: string | null;
  event_type: "source_itinerary_updated" | "correction_accepted";
  severity: "critical" | "warning" | "info";
  title: string;
  content: string;
  is_read: boolean;
  read_at: string | null;
  source_itinerary_id: string | null;
  forked_itinerary_id: string | null;
  source_snapshot_id: string | null;
  correction_id: string | null;
  poi_id: string | null;
  extra_payload: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type UserNotificationListResponse = {
  items: UserNotificationResponse[];
  total: number;
  unread_count: number;
  offset: number;
  limit: number;
};

export type MarkAllNotificationsReadResponse = {
  updated_count: number;
};

export type CollabLinkResponse = {
  id: string;
  itinerary_id: string;
  permission: "edit" | "read";
  share_code_last4: string;
  is_revoked: boolean;
  created_by_user_id: string;
  created_at: string;
  revoked_at: string | null;
};

export type CollabLinkCreateResponse = {
  link: CollabLinkResponse;
  share_code: string;
  share_url: string;
};

export type CollabLinkListResponse = {
  items: CollabLinkResponse[];
};

export type CollabHistoryItem = {
  id: string;
  itinerary_id: string;
  actor_type: "system" | "user" | "guest";
  actor_user_id: string | null;
  guest_name: string | null;
  event_type: string;
  target_type: string | null;
  target_id: string | null;
  payload: Record<string, unknown>;
  created_at: string;
};

export type CollabHistoryListResponse = {
  items: CollabHistoryItem[];
  total: number;
  offset: number;
  limit: number;
};

export type CollabParticipant = {
  session_id: string;
  participant_type: "user" | "guest";
  participant_user_id: string | null;
  display_name: string;
  permission: "edit" | "read";
  joined_at: string;
  cursor: Record<string, unknown> | null;
};

export type CollabCodeResolveResponse = {
  itinerary_id: string;
  itinerary_title: string;
  permission: "edit" | "read";
  collab_grant: string;
  expires_in: number;
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
  ticket_rules: PoiTicketRuleItem[];
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
  start_date?: string | null;
};

export type ItineraryWeatherDayResponse = {
  day_index: number;
  date: string;
  text: string;
  icon: string;
  temp_min: number | null;
  temp_max: number | null;
};

export type ItineraryWeatherResponse = {
  itinerary_id: string;
  start_date: string;
  items: ItineraryWeatherDayResponse[];
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

function authHeaders(token?: string, collabGrant?: string): HeadersInit {
  const headers: Record<string, string> = {};
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (collabGrant) {
    headers["X-Collab-Grant"] = collabGrant;
  }
  return headers;
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
  token: string,
  collabGrant?: string
): Promise<ItineraryResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token, collabGrant),
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

export async function fetchPricingAudiences(): Promise<PricingAudienceListResponse> {
  const response = await fetch(`${API_BASE_URL}/pois/pricing/audiences`);
  return parseJsonResponse<PricingAudienceListResponse>(response, "List pricing audiences request");
}

export async function fetchPoiTicketRules(poiId: string): Promise<PoiTicketRuleListResponse> {
  const response = await fetch(`${API_BASE_URL}/pois/${poiId}/ticket-rules`);
  return parseJsonResponse<PoiTicketRuleListResponse>(response, "List POI ticket rules request");
}

export async function upsertPoiTicketRules(
  poiId: string,
  payload: { items: PoiTicketRuleUpsert[] }
): Promise<PoiTicketRuleListResponse> {
  const response = await fetch(`${API_BASE_URL}/pois/${poiId}/ticket-rules`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<PoiTicketRuleListResponse>(response, "Upsert POI ticket rules request");
}

export async function fetchPoiCorrectionTypes(): Promise<PoiCorrectionTypeListResponse> {
  const response = await fetch(`${API_BASE_URL}/corrections/types`);
  return parseJsonResponse<PoiCorrectionTypeListResponse>(response, "List correction types request");
}

export async function submitPoiCorrection(
  poiId: string,
  token: string,
  payload: {
    type_code: string;
    proposed_value?: string | null;
    details?: string | null;
    photo?: File | null;
    source_itinerary_id?: string | null;
  }
): Promise<PoiCorrectionResponse> {
  const form = new FormData();
  form.set("type_code", payload.type_code);
  if (payload.proposed_value !== undefined && payload.proposed_value !== null) {
    form.set("proposed_value", payload.proposed_value);
  }
  if (payload.details !== undefined && payload.details !== null) {
    form.set("details", payload.details);
  }
  if (payload.source_itinerary_id) {
    form.set("source_itinerary_id", payload.source_itinerary_id);
  }
  if (payload.photo) {
    form.set("photo", payload.photo);
  }
  const response = await fetch(`${API_BASE_URL}/corrections/pois/${poiId}`, {
    method: "POST",
    headers: authHeaders(token),
    body: form
  });
  return parseJsonResponse<PoiCorrectionResponse>(response, "Submit POI correction request");
}

export async function fetchMyCorrections(
  token: string,
  offset = 0,
  limit = 20
): Promise<PoiCorrectionListResponse> {
  const response = await fetch(`${API_BASE_URL}/corrections/mine?offset=${offset}&limit=${limit}`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<PoiCorrectionListResponse>(response, "List my corrections request");
}

export async function fetchReviewCorrections(
  token: string,
  offset = 0,
  limit = 20
): Promise<PoiCorrectionListResponse> {
  const response = await fetch(`${API_BASE_URL}/corrections/review?offset=${offset}&limit=${limit}`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<PoiCorrectionListResponse>(response, "List review corrections request");
}

export async function fetchTerritories(): Promise<TerritoryRegionListResponse> {
  const response = await fetch(`${API_BASE_URL}/territories`);
  return parseJsonResponse<TerritoryRegionListResponse>(response, "List territories request");
}

export async function fetchTerritory(territoryId: string): Promise<TerritoryRegionResponse> {
  const response = await fetch(`${API_BASE_URL}/territories/${territoryId}`);
  return parseJsonResponse<TerritoryRegionResponse>(response, "Get territory request");
}

export async function submitTerritoryApplication(
  token: string,
  payload: { territory_id: string; reason?: string | null }
): Promise<TerritoryGuardianApplicationResponse> {
  const response = await fetch(`${API_BASE_URL}/territories/applications`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<TerritoryGuardianApplicationResponse>(
    response,
    "Submit territory application request"
  );
}

export async function territoryGuardianCheckIn(
  territoryId: string,
  token: string
): Promise<TerritoryGuardianCheckInResponse> {
  const response = await fetch(`${API_BASE_URL}/territories/${territoryId}/check-in`, {
    method: "POST",
    headers: authHeaders(token)
  });
  return parseJsonResponse<TerritoryGuardianCheckInResponse>(
    response,
    "Territory guardian check-in request"
  );
}

export async function fetchAdminTerritoryApplications(
  token: string,
  status: "pending" | "approved" | "rejected" | "all" = "pending",
  offset = 0,
  limit = 50
): Promise<TerritoryGuardianApplicationListResponse> {
  const response = await fetch(
    `${API_BASE_URL}/admin/territories/applications?status=${status}&offset=${offset}&limit=${limit}`,
    { headers: authHeaders(token) }
  );
  return parseJsonResponse<TerritoryGuardianApplicationListResponse>(
    response,
    "List admin territory applications request"
  );
}

export async function reviewAdminTerritoryApplication(
  applicationId: string,
  token: string,
  payload: { action: "approve" | "reject"; review_comment?: string | null }
): Promise<TerritoryGuardianApplicationResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/territories/applications/${applicationId}/review`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<TerritoryGuardianApplicationResponse>(
    response,
    "Review admin territory application request"
  );
}

export async function rebuildTerritories(token: string): Promise<TerritoryRebuildResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/territories/rebuild`, {
    method: "POST",
    headers: authHeaders(token)
  });
  return parseJsonResponse<TerritoryRebuildResponse>(response, "Rebuild territories request");
}

export async function fetchGuardianReputation(
  token: string
): Promise<TerritoryGuardianReputationListResponse> {
  const response = await fetch(`${API_BASE_URL}/admin/territories/guardians/reputation`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<TerritoryGuardianReputationListResponse>(
    response,
    "List guardian reputation request"
  );
}

export async function resumeGuardian(guardianId: string, token: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/admin/territories/guardians/${guardianId}/resume`, {
    method: "POST",
    headers: authHeaders(token)
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`Resume guardian request failed with ${response.status}. Response: ${text.slice(0, 120)}`);
  }
}

export async function reviewPoiCorrection(
  correctionId: string,
  token: string,
  payload: { action: "accepted" | "rejected"; review_comment?: string | null }
): Promise<PoiCorrectionReviewResponse> {
  const response = await fetch(`${API_BASE_URL}/corrections/${correctionId}/review`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json; charset=utf-8"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<PoiCorrectionReviewResponse>(response, "Review POI correction request");
}

export async function fetchNotifications(
  token: string,
  offset = 0,
  limit = 20,
  unreadOnly = false
): Promise<UserNotificationListResponse> {
  const response = await fetch(
    `${API_BASE_URL}/notifications?offset=${offset}&limit=${limit}&unread_only=${unreadOnly ? "true" : "false"}`,
    {
      headers: authHeaders(token)
    }
  );
  return parseJsonResponse<UserNotificationListResponse>(response, "List notifications request");
}

export async function markNotificationRead(
  notificationId: string,
  token: string,
  read = true
): Promise<UserNotificationResponse> {
  const response = await fetch(`${API_BASE_URL}/notifications/${notificationId}/read`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ read })
  });
  return parseJsonResponse<UserNotificationResponse>(response, "Mark notification read request");
}

export async function markAllNotificationsRead(token: string): Promise<MarkAllNotificationsReadResponse> {
  const response = await fetch(`${API_BASE_URL}/notifications/read-all`, {
    method: "POST",
    headers: authHeaders(token)
  });
  return parseJsonResponse<MarkAllNotificationsReadResponse>(response, "Mark all notifications read request");
}

export async function createCollabLink(
  itineraryId: string,
  token: string,
  permission: "edit" | "read" = "edit"
): Promise<CollabLinkCreateResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/collab/links`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ permission })
  });
  return parseJsonResponse<CollabLinkCreateResponse>(response, "Create collab link request");
}

export async function fetchCollabLinks(itineraryId: string, token: string): Promise<CollabLinkListResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/collab/links`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<CollabLinkListResponse>(response, "List collab links request");
}

export async function updateCollabLink(
  itineraryId: string,
  linkId: string,
  token: string,
  payload: { permission?: "edit" | "read"; revoke?: boolean }
): Promise<CollabLinkResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/collab/links/${linkId}`, {
    method: "PATCH",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<CollabLinkResponse>(response, "Update collab link request");
}

export async function fetchCollabHistory(
  itineraryId: string,
  token: string,
  offset = 0,
  limit = 50,
  collabGrant?: string
): Promise<CollabHistoryListResponse> {
  const response = await fetch(
    `${API_BASE_URL}/itineraries/${itineraryId}/collab/history?offset=${offset}&limit=${limit}`,
    {
      headers: authHeaders(token, collabGrant)
    }
  );
  return parseJsonResponse<CollabHistoryListResponse>(response, "List collab history request");
}

export async function fetchItineraryItemsWithPoi(
  itineraryId: string,
  token: string,
  collabGrant?: string
): Promise<ItineraryItemsWithPoiListResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items`, {
    headers: authHeaders(token, collabGrant)
  });
  return parseJsonResponse<ItineraryItemsWithPoiListResponse>(response, "List itinerary items request");
}

export async function fetchItineraryById(
  itineraryId: string,
  token: string,
  collabGrant?: string
): Promise<ItineraryResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}`, {
    headers: authHeaders(token, collabGrant)
  });
  return parseJsonResponse<ItineraryResponse>(response, "Get itinerary request");
}

export async function fetchItineraryWeather(
  itineraryId: string,
  token: string,
  forceRefresh = false,
  collabGrant?: string
): Promise<ItineraryWeatherResponse> {
  const response = await fetch(
    `${API_BASE_URL}/itineraries/${itineraryId}/weather?force_refresh=${forceRefresh ? "true" : "false"}`,
    { headers: authHeaders(token, collabGrant) }
  );
  return parseJsonResponse<ItineraryWeatherResponse>(response, "Fetch itinerary weather request");
}

export async function fetchPublicItineraries(offset = 0, limit = 20): Promise<PublicItineraryListResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries?offset=${offset}&limit=${limit}`);
  return parseJsonResponse<PublicItineraryListResponse>(response, "List public itineraries request");
}

export async function fetchExploreHeatmap(limit = 20): Promise<ExploreHeatPointListResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/heatmap?limit=${limit}`);
  return parseJsonResponse<ExploreHeatPointListResponse>(response, "List explore heatmap request");
}

export async function fetchExploreRecommendations(
  limit = 12,
  token?: string
): Promise<ExploreRecommendationListResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/recommendations?limit=${limit}`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<ExploreRecommendationListResponse>(response, "List explore recommendations request");
}

export async function fetchPublicItinerary(itineraryId: string): Promise<PublicItineraryResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries/${itineraryId}`);
  return parseJsonResponse<PublicItineraryResponse>(response, "Get public itinerary request");
}

export async function fetchPublicItineraryShareMeta(itineraryId: string): Promise<PublicItineraryShareMetaResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries/${itineraryId}/share-meta`);
  return parseJsonResponse<PublicItineraryShareMetaResponse>(response, "Get public itinerary share meta request");
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

export async function recordPublicItineraryView(
  itineraryId: string,
  token: string
): Promise<ExploreVisitLogResponse> {
  const response = await fetch(`${API_BASE_URL}/explore/itineraries/${itineraryId}/view`, {
    method: "POST",
    headers: authHeaders(token)
  });
  return parseJsonResponse<ExploreVisitLogResponse>(response, "Record public itinerary view request");
}

export async function fetchItineraryDiff(itineraryId: string, token: string): Promise<ItineraryDiffResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/diff`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<ItineraryDiffResponse>(response, "Fetch itinerary diff request");
}

export async function submitItineraryDiffActionsBatch(
  itineraryId: string,
  sourceSnapshotId: string,
  actions: ItineraryDiffActionInput[],
  token: string
): Promise<ItineraryDiffActionBatchResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/diff/actions:batch`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      source_snapshot_id: sourceSnapshotId,
      actions
    })
  });
  return parseJsonResponse<ItineraryDiffActionBatchResponse>(response, "Submit itinerary diff actions request");
}

export async function fetchItineraryDiffActionStatuses(
  itineraryId: string,
  sourceSnapshotId: string,
  token: string
): Promise<ItineraryDiffActionStatusResponse> {
  const response = await fetch(
    `${API_BASE_URL}/itineraries/${itineraryId}/diff/actions?source_snapshot_id=${sourceSnapshotId}`,
    { headers: authHeaders(token) }
  );
  return parseJsonResponse<ItineraryDiffActionStatusResponse>(
    response,
    "Fetch itinerary diff action statuses request"
  );
}

export async function createItineraryItem(
  itineraryId: string,
  payload: ItineraryItemCreatePayload,
  token: string,
  collabGrant?: string
): Promise<ItineraryItemResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items`, {
    method: "POST",
    headers: {
      ...authHeaders(token, collabGrant),
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
  token: string,
  collabGrant?: string
): Promise<ItineraryItemResponse> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items/${itemId}`, {
    method: "PUT",
    headers: {
      ...authHeaders(token, collabGrant),
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });
  return parseJsonResponse<ItineraryItemResponse>(response, "Update itinerary item request");
}

export async function deleteItineraryItem(
  itineraryId: string,
  itemId: string,
  token: string,
  collabGrant?: string
): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/itineraries/${itineraryId}/items/${itemId}`, {
    method: "DELETE",
    headers: authHeaders(token, collabGrant)
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(
      `Delete itinerary item request failed with ${response.status}. Response: ${text.slice(0, 120)}`
    );
  }
}

export async function resolveCollabCode(
  code: string,
  token: string
): Promise<CollabCodeResolveResponse> {
  const response = await fetch(`${API_BASE_URL}/collab/code/resolve`, {
    method: "POST",
    headers: {
      ...authHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ code })
  });
  return parseJsonResponse<CollabCodeResolveResponse>(response, "Resolve collab code request");
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

export async function fetchMyPassport(token: string): Promise<PassportResponse> {
  const response = await fetch(`${API_BASE_URL}/passports/me`, {
    headers: authHeaders(token)
  });
  return parseJsonResponse<PassportResponse>(response, "Fetch my passport request");
}
