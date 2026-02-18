import type { ItineraryItemPoiSnapshot, PoiResponse } from "../api";

export type TimelineDraftItem = {
  clientId: string;
  itemId: string | null;
  itineraryId: string;
  dayIndex: number;
  sortOrder: number;
  startTime: string | null;
  durationMinutes: number | null;
  cost: number | null;
  tips: string | null;
  poi: ItineraryItemPoiSnapshot;
};

export type TimelineItemPatch = {
  startTime?: string | null;
  durationMinutes?: number | null;
  cost?: number | null;
  tips?: string | null;
};

export type AddTimelineBlockPayload = {
  poiId: string;
  poi: PoiResponse;
  dayIndex: number;
  startTime: string | null;
  durationMinutes: number | null;
  cost: number | null;
  tips: string | null;
};
