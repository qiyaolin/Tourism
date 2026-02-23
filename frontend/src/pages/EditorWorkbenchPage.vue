<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  createCollabLink,
  createItineraryItem,
  deleteItinerary,
  deleteItineraryItem,
  fetchCollabHistory,
  fetchCollabLinks,
  fetchItineraries,
  fetchItineraryById,
  fetchItineraryDiff,
  fetchItineraryDiffActionStatuses,
  fetchItineraryItemsWithPoi,
  fetchItineraryWeather,
  fetchPois,
  submitItineraryDiffActionsBatch,
  updateCollabLink,
  updateItinerary,
  updateItineraryItem,
  type CollabHistoryItem,
  type CollabLinkResponse,
  type ItineraryDiffActionInput,
  type ItineraryDiffResponse,
  type ItineraryItemCreatePayload,
  type ItineraryItemWithPoi,
  type ItineraryResponse,
  type ItineraryWeatherDayResponse,
  type PoiResponse
} from "../api";
import AiPlanGenerator from "../components/AiPlanGenerator.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import ItineraryDiffPanel from "../components/ItineraryDiffPanel.vue";
import PoiInfoCard from "../components/PoiInfoCard.vue";
import TimelineEditor from "../components/TimelineEditor.vue";
import TimelineWeatherStrip from "../components/TimelineWeatherStrip.vue";
import CollabPanel from "../components/CollabPanel.vue";
import CollabAvatarBar from "../components/CollabAvatarBar.vue";
import { computeDraftItemsDiff } from "../utils/collabDiff";
import { useAmap } from "../composables/useAmap";
import { useAuth } from "../composables/useAuth";
import { useYjsCollab } from "../composables/useYjsCollab";
import type { AddTimelineBlockPayload, TimelineDraftItem, TimelineItemPatch } from "../types/timeline";
import { isCnPhone, normalizePhone } from "../utils/validators";

const phone = ref("");
const code = ref("");
const nickname = ref("");
const sendCooldown = ref(0);

const mapHost = ref<HTMLElement | null>(null);
const mapLoading = ref(false);
const mapError = ref("");
const itineraryLoading = ref(false);
const itineraryError = ref("");

const itineraries = ref<ItineraryResponse[]>([]);
const selectedItineraryId = ref("");
const baselineItems = ref<ItineraryItemWithPoi[]>([]);
const draftItems = ref<TimelineDraftItem[]>([]);
const activeDay = ref(1);
const activeItemClientId = ref("");

const poiCatalog = ref<PoiResponse[]>([]);
const poiLoading = ref(false);
const poiError = ref("");

const savePending = ref(false);
const saveError = ref("");
const saveSuccess = ref("");
const dirty = ref(false);
const discardDialogOpen = ref(false);
const diffOpen = ref(false);
const diffLoading = ref(false);
const diffError = ref("");
const diffData = ref<ItineraryDiffResponse | null>(null);
const diffActionQueue = ref<Record<string, ItineraryDiffActionInput>>({});
const diffSubmitPending = ref(false);
const diffSubmitError = ref("");
const diffSubmitWarnings = ref<string[]>([]);
const itineraryStartDateDraft = ref("");
const weatherItems = ref<ItineraryWeatherDayResponse[]>([]);
const weatherLoading = ref(false);
const weatherError = ref("");
const collabLinks = ref<CollabLinkResponse[]>([]);
const collabHistory = ref<CollabHistoryItem[]>([]);
const collabHistoryLoading = ref(false);
const collabError = ref("");
const collabShareUrl = ref("");
const collabCreatePending = ref(false);
const collabPermissionDraft = ref<"edit" | "read">("edit");
const applyingRemoteCollab = ref(false);
const collabShareCode = ref("");

const markerKeyToClientId = new Map<string, string>();
const route = useRoute();

const {
  user,
  loading,
  error,
  debugCode,
  isLoggedIn,
  token,
  sendLoginCode,
  loginWithCode,
  clearAuth,
  loadMe,
  getCollabGrant,
  clearCollabGrant
} = useAuth();

const { mapReady, initMap, renderMarkers, focusMarker, clearMarkers, destroyMap } = useAmap(mapHost);

const selectedItinerary = computed(
  () => itineraries.value.find((item) => item.id === selectedItineraryId.value) || null
);
const authError = computed(() => error.value);
const isDirty = computed(() => dirty.value && !savePending.value);
const isForkedItinerary = computed(() => Boolean(selectedItinerary.value?.fork_source_itinerary_id));
const hasStartDate = computed(() => Boolean(selectedItinerary.value?.start_date));
const selectedCollabGrantEntry = computed(() => getCollabGrant(selectedItineraryId.value));
const selectedCollabGrant = computed(() => selectedCollabGrantEntry.value?.grant || "");
const canManageCollabLinks = computed(
  () => Boolean(selectedItinerary.value && user.value && selectedItinerary.value.creator_user_id === user.value.id)
);
const canSaveToServer = computed(() => {
  if (!token.value || !selectedItineraryId.value) {
    return false;
  }
  if (canManageCollabLinks.value) {
    return true;
  }
  return selectedCollabGrantEntry.value?.permission === "edit";
});

const selectedMapItem = computed<ItineraryItemWithPoi | null>(() => {
  const target = draftItems.value.find((item) => item.clientId === activeItemClientId.value);
  if (!target) {
    return null;
  }
  return toMapItem(target);
});
const { participants: collabParticipants, permission: collabPermission, connected: collabConnected, error: collabWsError, remoteCursors, disconnect, connect, pushLocalState, sendCursor, sendHistoryUpdate } = useYjsCollab({
  itineraryId: () => selectedItineraryId.value,
  authToken: () => token.value || "",
  collabGrant: () => selectedCollabGrant.value,
  getLocalState: () => currentCollabState(),
  applyRemoteState: (state) => applyRemoteCollabState(state)
});
const meaningfulCollabHistory = computed(() =>
  collabHistory.value.filter((item) => {
    if (item.event_type !== "content_sync" && item.event_type !== "y_update") {
      return false;
    }
    const payload = item.payload || {};
    // Only show entries with specific descriptions from the 10s diff timer.
    // These always contain 【】 markers (e.g., "在【故宫】将【预算花费】从 ...").
    // Generic fallbacks like "编辑了协作内容" or "更新了时间轴内容" are useless.
    const description = typeof payload.description === "string" ? payload.description : "";
    return description.includes("【");
  })
);

let timer: ReturnType<typeof setInterval> | null = null;
let collabSyncTimer: ReturnType<typeof setTimeout> | null = null;
let collabHistoryPollTimer: ReturnType<typeof setInterval> | null = null;
let collabHistorySyncing = false;
const COLLAB_HISTORY_POLL_INTERVAL_MS = 6000;

// 10s diff timer for collaboration history
let collabDiffTimer: ReturnType<typeof setInterval> | null = null;
let lastDiffSnapshotItems: TimelineDraftItem[] = [];

function startCollabDiffTimer() {
  stopCollabDiffTimer();
  lastDiffSnapshotItems = JSON.parse(JSON.stringify(draftItems.value));
  collabDiffTimer = setInterval(() => {
    if (collabPermission.value !== "edit") return;
    const currentItems = draftItems.value;
    const diffs = computeDraftItemsDiff(lastDiffSnapshotItems, currentItems);
    lastDiffSnapshotItems = JSON.parse(JSON.stringify(currentItems));
    if (diffs.length > 0) {
      const descriptions = diffs.map((d) => d.description);
      const description = descriptions.slice(0, 3).join("\uff1b") + (descriptions.length > 3 ? " \u7b49" : "");
      sendHistoryUpdate(description);
    }
  }, 10000);
}

function stopCollabDiffTimer() {
  if (collabDiffTimer) {
    clearInterval(collabDiffTimer);
    collabDiffTimer = null;
  }
}

function makeClientId() {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `tmp-${crypto.randomUUID()}`;
  }
  return `tmp-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
}

function normalizeTime(value: string | null): string | null {
  if (!value) {
    return null;
  }
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const match = trimmed.match(/^(\d{2}):(\d{2})(?::\d{2})?$/);
  if (!match) {
    return trimmed;
  }
  return `${match[1]}:${match[2]}:00`;
}

function startCooldown(seconds: number) {
  sendCooldown.value = seconds;
  if (timer) {
    clearInterval(timer);
  }
  timer = setInterval(() => {
    sendCooldown.value -= 1;
    if (sendCooldown.value <= 0) {
      sendCooldown.value = 0;
      if (timer) {
        clearInterval(timer);
        timer = null;
      }
    }
  }, 1000);
}

async function handleSendCode() {
  const normalized = normalizePhone(phone.value);
  if (!isCnPhone(normalized)) {
    return;
  }
  phone.value = normalized;
  const result = await sendLoginCode(normalized);
  startCooldown(60);
  if (result.debug_code) {
    code.value = result.debug_code;
  }
}

async function handleLogin() {
  const normalized = normalizePhone(phone.value);
  if (!isCnPhone(normalized)) {
    return;
  }
  phone.value = normalized;
  await loginWithCode(normalized, code.value.trim(), nickname.value.trim());
}

function toDraftItem(item: ItineraryItemWithPoi): TimelineDraftItem {
  return {
    clientId: item.item_id,
    itemId: item.item_id,
    itineraryId: item.itinerary_id,
    dayIndex: item.day_index,
    sortOrder: item.sort_order,
    startTime: item.start_time,
    durationMinutes: item.duration_minutes,
    cost: item.cost,
    tips: item.tips,
    poi: item.poi
  };
}

function toMapItem(item: TimelineDraftItem): ItineraryItemWithPoi {
  return {
    item_id: item.itemId || item.clientId,
    itinerary_id: item.itineraryId,
    day_index: item.dayIndex,
    sort_order: item.sortOrder,
    start_time: item.startTime,
    duration_minutes: item.durationMinutes,
    cost: item.cost,
    tips: item.tips,
    poi: item.poi
  };
}

function toCreatePayload(item: TimelineDraftItem): ItineraryItemCreatePayload {
  return {
    day_index: item.dayIndex,
    sort_order: item.sortOrder,
    poi_id: item.poi.id,
    start_time: normalizeTime(item.startTime),
    duration_minutes: item.durationMinutes,
    cost: item.cost,
    tips: item.tips
  };
}

function serializeDraftItem(item: TimelineDraftItem): Record<string, unknown> {
  return {
    client_id: item.clientId,
    item_id: item.itemId,
    itinerary_id: item.itineraryId,
    day_index: item.dayIndex,
    sort_order: item.sortOrder,
    start_time: item.startTime,
    duration_minutes: item.durationMinutes,
    cost: item.cost,
    tips: item.tips,
    poi: item.poi
  };
}

function deserializeDraftItem(raw: unknown): TimelineDraftItem | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    return null;
  }
  const row = raw as Record<string, unknown>;
  const poi = row.poi;
  if (!poi || typeof poi !== "object" || Array.isArray(poi)) {
    return null;
  }
  const poiRecord = poi as Record<string, unknown>;
  if (typeof poiRecord.id !== "string" || typeof poiRecord.name !== "string" || typeof poiRecord.type !== "string") {
    return null;
  }
  const dayIndex = Number(row.day_index);
  const sortOrder = Number(row.sort_order);
  if (!Number.isFinite(dayIndex) || !Number.isFinite(sortOrder)) {
    return null;
  }
  return {
    clientId: typeof row.client_id === "string" ? row.client_id : makeClientId(),
    itemId: typeof row.item_id === "string" ? row.item_id : null,
    itineraryId: typeof row.itinerary_id === "string" ? row.itinerary_id : selectedItineraryId.value,
    dayIndex: Math.max(1, Math.floor(dayIndex)),
    sortOrder: Math.max(1, Math.floor(sortOrder)),
    startTime: typeof row.start_time === "string" ? row.start_time : null,
    durationMinutes:
      typeof row.duration_minutes === "number" && Number.isFinite(row.duration_minutes)
        ? Math.max(1, Math.floor(row.duration_minutes))
        : null,
    cost: typeof row.cost === "number" && Number.isFinite(row.cost) ? row.cost : null,
    tips: typeof row.tips === "string" ? row.tips : null,
    poi: {
      id: poiRecord.id,
      name: poiRecord.name,
      type: poiRecord.type,
      longitude: typeof poiRecord.longitude === "number" ? poiRecord.longitude : 0,
      latitude: typeof poiRecord.latitude === "number" ? poiRecord.latitude : 0,
      address: typeof poiRecord.address === "string" ? poiRecord.address : null,
      opening_hours: typeof poiRecord.opening_hours === "string" ? poiRecord.opening_hours : null,
      ticket_price: typeof poiRecord.ticket_price === "number" ? poiRecord.ticket_price : null,
      ticket_rules: Array.isArray(poiRecord.ticket_rules) ? (poiRecord.ticket_rules as never[]) : []
    }
  };
}

function currentCollabState() {
  return {
    start_date: itineraryStartDateDraft.value || "",
    items: draftItems.value.map((item) => serializeDraftItem(item))
  };
}

function applyRemoteCollabState(state: { start_date: string; items: unknown[] }) {
  applyingRemoteCollab.value = true;
  try {
    itineraryStartDateDraft.value = typeof state.start_date === "string" ? state.start_date : "";
    const parsedItems = Array.isArray(state.items)
      ? state.items.map((item) => deserializeDraftItem(item)).filter((item): item is TimelineDraftItem => item !== null)
      : [];

    // compute diffs to find what changed, so we can animate UI
    const diffs = computeDraftItemsDiff(draftItems.value, parsedItems);
    const changedTargets = new Set(diffs.filter(d => d.type === "modify" || d.type === "reorder").map(d => d.targetName));

    draftItems.value = parsedItems
      .slice()
      .sort((a, b) => a.dayIndex - b.dayIndex || a.sortOrder - b.sortOrder);
    
    // flash the changed items
    if (changedTargets.size > 0 && typeof document !== "undefined") {
      import("vue").then(({ nextTick }) => {
        nextTick(() => {
          document.querySelectorAll(".timeline-block-title").forEach(titleEl => {
            if (changedTargets.has(titleEl.textContent?.trim() || "")) {
              const blockEl = titleEl.closest(".timeline-block");
              if (blockEl) {
                blockEl.classList.add("remote-updated");
                setTimeout(() => blockEl.classList.remove("remote-updated"), 800);
              }
            }
          });
        });
      });
    }

    const maxDay = draftItems.value.reduce((max, item) => Math.max(max, item.dayIndex), 1);
    if (selectedItinerary.value) {
      // Preserve manually-added empty days: only grow, never shrink
      selectedItinerary.value.days = Math.max(selectedItinerary.value.days || 1, maxDay);
    }
    const first = draftItems.value[0] || null;
    if (!first) {
      activeItemClientId.value = "";
      activeDay.value = 1;
    } else if (!draftItems.value.some((item) => item.clientId === activeItemClientId.value)) {
      activeItemClientId.value = first.clientId;
      activeDay.value = first.dayIndex;
    }
    dirty.value = true;
    // Refresh the diff snapshot so the 10s timer doesn't re-report remote changes
    lastDiffSnapshotItems = JSON.parse(JSON.stringify(draftItems.value));
    saveSuccess.value = "已同步协作者修改（尚未保存到服务器）";
    // Do NOT re-render map markers here; remote updates should only
    // affect the timeline UI, not cause the map to jitter.
  } finally {
    // Vue watchers are async. Use nextTick to unset the flag AFTER watchers have run.
    import("vue").then(({ nextTick }) => {
      nextTick(() => {
        applyingRemoteCollab.value = false;
      });
    });
  }
}

function resetItineraryState() {
  stopCollabHistoryPolling();
  itineraries.value = [];
  selectedItineraryId.value = "";
  baselineItems.value = [];
  draftItems.value = [];
  activeDay.value = 1;
  activeItemClientId.value = "";
  itineraryError.value = "";
  saveError.value = "";
  saveSuccess.value = "";
  dirty.value = false;
  diffOpen.value = false;
  diffLoading.value = false;
  diffError.value = "";
  diffData.value = null;
  diffActionQueue.value = {};
  diffSubmitPending.value = false;
  diffSubmitError.value = "";
  diffSubmitWarnings.value = [];
  itineraryStartDateDraft.value = "";
  weatherItems.value = [];
  weatherLoading.value = false;
  weatherError.value = "";
  collabLinks.value = [];
  collabHistory.value = [];
  collabHistoryLoading.value = false;
  collabError.value = "";
  collabShareCode.value = "";
  collabShareUrl.value = "";
  collabCreatePending.value = false;
  applyingRemoteCollab.value = false;
  markerKeyToClientId.clear();
  clearMarkers();
  disconnect();
}

function resetDiffState(keepOpen = false) {
  diffLoading.value = false;
  diffError.value = "";
  diffData.value = null;
  diffActionQueue.value = {};
  diffSubmitPending.value = false;
  diffSubmitError.value = "";
  diffSubmitWarnings.value = [];
  if (!keepOpen) {
    diffOpen.value = false;
  }
}

async function loadDiffData(force = false) {
  if (!token.value || !selectedItineraryId.value || !isForkedItinerary.value) {
    resetDiffState();
    return;
  }
  if (!force && diffData.value) {
    return;
  }
  diffLoading.value = true;
  diffError.value = "";
  try {
    diffData.value = await fetchItineraryDiff(selectedItineraryId.value, token.value);
    const statuses = await fetchItineraryDiffActionStatuses(
      selectedItineraryId.value,
      diffData.value.source_snapshot_id,
      token.value
    );
    const statusMap: Record<string, string> = {};
    for (const item of statuses.items) {
      statusMap[item.diff_key] = item.action;
    }
    diffData.value.action_statuses = {
      ...diffData.value.action_statuses,
      ...statusMap
    };
  } catch (e) {
    diffData.value = null;
    diffError.value = e instanceof Error ? e.message : "加载修改对比失败";
  } finally {
    diffLoading.value = false;
  }
}

async function toggleDiffPanel() {
  if (!isForkedItinerary.value) {
    return;
  }
  diffOpen.value = !diffOpen.value;
  if (diffOpen.value) {
    await loadDiffData();
  }
}

function parseItemKey(key: string): { dayIndex: number; sortOrder: number } | null {
  const match = key.match(/^d(\d+)-s(\d+)$/);
  if (!match) {
    return null;
  }
  return { dayIndex: Number(match[1]), sortOrder: Number(match[2]) };
}

function findDraftIndexByItemKey(itemKey: string): number {
  const parsed = parseItemKey(itemKey);
  if (!parsed) {
    return -1;
  }
  return draftItems.value.findIndex(
    (item) => item.dayIndex === parsed.dayIndex && item.sortOrder === parsed.sortOrder
  );
}

function normalizeNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeString(value: unknown): string | null {
  if (value === null || value === undefined) {
    return null;
  }
  const text = String(value).trim();
  return text ? text : null;
}

function applyMetadataField(field: string, value: unknown) {
  const current = selectedItinerary.value;
  if (!current) {
    return;
  }
  const target = itineraries.value.find((item) => item.id === current.id);
  if (!target) {
    return;
  }
  if (field === "title" && typeof value === "string") {
    target.title = value;
    return;
  }
  if (field === "destination" && typeof value === "string") {
    target.destination = value;
    return;
  }
  if (field === "days") {
    const days = normalizeNumber(value);
    if (days !== null) {
      target.days = Math.max(1, Math.floor(days));
    }
    return;
  }
  if (field === "status" && typeof value === "string") {
    target.status = value;
    return;
  }
  if (field === "visibility" && typeof value === "string") {
    target.visibility = value;
    return;
  }
  if (field === "cover_image_url") {
    target.cover_image_url = normalizeString(value);
  }
}

function applyModifiedField(itemKey: string, field: string, value: unknown) {
  const index = findDraftIndexByItemKey(itemKey);
  if (index < 0) {
    return;
  }
  const item = draftItems.value[index];
  if (field === "day_index") {
    const num = normalizeNumber(value);
    if (num !== null) {
      item.dayIndex = Math.max(1, Math.floor(num));
    }
    return;
  }
  if (field === "sort_order") {
    const num = normalizeNumber(value);
    if (num !== null) {
      item.sortOrder = Math.max(1, Math.floor(num));
    }
    return;
  }
  if (field === "start_time") {
    item.startTime = normalizeString(value);
    return;
  }
  if (field === "duration_minutes") {
    item.durationMinutes = normalizeNumber(value);
    return;
  }
  if (field === "cost") {
    item.cost = normalizeNumber(value);
    return;
  }
  if (field === "tips") {
    item.tips = normalizeString(value);
    return;
  }
  if (field === "poi_id" && typeof value === "string") {
    item.poi.id = value;
    return;
  }
  if (field === "poi_name" && typeof value === "string") {
    item.poi.name = value;
    return;
  }
  if (field === "poi_type" && typeof value === "string") {
    item.poi.type = value;
    return;
  }
  if (field === "longitude") {
    const num = normalizeNumber(value);
    if (num !== null) {
      item.poi.longitude = num;
    }
    return;
  }
  if (field === "latitude") {
    const num = normalizeNumber(value);
    if (num !== null) {
      item.poi.latitude = num;
    }
    return;
  }
  if (field === "address") {
    item.poi.address = normalizeString(value);
    return;
  }
  if (field === "opening_hours") {
    item.poi.opening_hours = normalizeString(value);
    return;
  }
  if (field === "ticket_price") {
    item.poi.ticket_price = normalizeNumber(value);
  }
}

function restoreRemovedItem(itemKey: string, source: Record<string, unknown>) {
  const parsed = parseItemKey(itemKey);
  if (!parsed) {
    return;
  }
  const existingIndex = findDraftIndexByItemKey(itemKey);
  if (existingIndex >= 0) {
    return;
  }
  const poiId = normalizeString(source.poi_id);
  if (!poiId) {
    return;
  }
  draftItems.value.push({
    clientId: makeClientId(),
    itemId: null,
    itineraryId: selectedItineraryId.value,
    dayIndex: parsed.dayIndex,
    sortOrder: parsed.sortOrder,
    startTime: normalizeString(source.start_time),
    durationMinutes: normalizeNumber(source.duration_minutes),
    cost: normalizeNumber(source.cost),
    tips: normalizeString(source.tips),
      poi: {
        id: poiId,
        name: normalizeString(source.poi_name) || "未命名节点",
        type: normalizeString(source.poi_type) || "unknown",
        longitude: normalizeNumber(source.longitude) || 0,
        latitude: normalizeNumber(source.latitude) || 0,
        address: normalizeString(source.address),
        opening_hours: normalizeString(source.opening_hours),
        ticket_price: normalizeNumber(source.ticket_price),
        ticket_rules: []
      }
    });
}

function applyDiffActionLocally(payload: {
  diff_key: string;
  diff_type: ItineraryDiffActionInput["diff_type"];
  action: ItineraryDiffActionInput["action"];
  item_key?: string;
  field?: string;
  before?: unknown;
  after?: unknown;
  current?: Record<string, unknown>;
  source?: Record<string, unknown>;
}) {
  if (payload.action === "ignored" || payload.action === "read") {
    return;
  }
  if (payload.diff_type === "metadata" && payload.field) {
    applyMetadataField(payload.field, payload.action === "applied" ? payload.after : payload.before);
    return;
  }
  if (payload.diff_type === "modified" && payload.item_key && payload.field) {
    applyModifiedField(
      payload.item_key,
      payload.field,
      payload.action === "applied" ? payload.after : payload.before
    );
    dirty.value = true;
    return;
  }
  if (payload.diff_type === "added" && payload.item_key) {
    if (payload.action === "rolled_back") {
      const index = findDraftIndexByItemKey(payload.item_key);
      if (index >= 0) {
        draftItems.value.splice(index, 1);
        dirty.value = true;
      }
    }
    return;
  }
  if (payload.diff_type === "removed" && payload.item_key) {
    if (payload.action === "rolled_back" && payload.source) {
      restoreRemovedItem(payload.item_key, payload.source);
      dirty.value = true;
    }
  }
}

function stageDiffAction(payload: {
  diff_key: string;
  diff_type: ItineraryDiffActionInput["diff_type"];
  action: ItineraryDiffActionInput["action"];
  reason?: string | null;
  item_key?: string;
  field?: string;
  before?: unknown;
  after?: unknown;
  current?: Record<string, unknown>;
  source?: Record<string, unknown>;
}) {
  applyDiffActionLocally(payload);
  diffActionQueue.value[payload.diff_key] = {
    diff_key: payload.diff_key,
    diff_type: payload.diff_type,
    action: payload.action,
    reason: payload.reason || null
  };
  if (diffData.value) {
    diffData.value.action_statuses = {
      ...diffData.value.action_statuses,
      [payload.diff_key]: payload.action
    };
  }
}

async function submitQueuedDiffActions() {
  if (!token.value || !selectedItineraryId.value || !diffData.value) {
    return;
  }
  const actions = Object.values(diffActionQueue.value);
  if (actions.length === 0) {
    return;
  }
  diffSubmitPending.value = true;
  diffSubmitError.value = "";
  diffSubmitWarnings.value = [];
  try {
    const result = await submitItineraryDiffActionsBatch(
      selectedItineraryId.value,
      diffData.value.source_snapshot_id,
      actions,
      token.value
    );
    diffActionQueue.value = {};
    diffSubmitWarnings.value = result.warnings;
    diffData.value.action_statuses = {
      ...diffData.value.action_statuses,
      ...result.action_statuses
    };
  } catch (e) {
    diffSubmitError.value = e instanceof Error ? e.message : "提交 Diff 动作失败";
  } finally {
    diffSubmitPending.value = false;
  }
}

function jumpToDiffKey(itemKey: string) {
  const index = findDraftIndexByItemKey(itemKey);
  if (index < 0) {
    return;
  }
  const item = draftItems.value[index];
  activeDay.value = item.dayIndex;
  activeItemClientId.value = item.clientId;
  focusMarker(item.itemId || item.clientId);
}

function setActiveByClientId(clientId: string) {
  const target = draftItems.value.find((item) => item.clientId === clientId);
  if (!target) {
    return;
  }
  activeItemClientId.value = target.clientId;
  activeDay.value = target.dayIndex;
}

function renderCurrentMarkers() {
  if (!mapReady.value) {
    return;
  }
  markerKeyToClientId.clear();
  const markerItems = draftItems.value
    .slice()
    .sort((a, b) => a.dayIndex - b.dayIndex || a.sortOrder - b.sortOrder)
    .map((item) => {
      const markerKey = item.itemId || item.clientId;
      markerKeyToClientId.set(markerKey, item.clientId);
      return {
        ...toMapItem(item),
        item_id: markerKey
      };
    });

  renderMarkers(markerItems, (mapItem) => {
    const clientId = markerKeyToClientId.get(mapItem.item_id) || mapItem.item_id;
    setActiveByClientId(clientId);
    focusMarker(mapItem.item_id);
  });

  const active = draftItems.value.find((item) => item.clientId === activeItemClientId.value);
  if (active) {
    focusMarker(active.itemId || active.clientId);
  }
}

function selectItem(clientId: string) {
  setActiveByClientId(clientId);
  const target = draftItems.value.find((item) => item.clientId === clientId);
  if (!target) {
    return;
  }
  focusMarker(target.itemId || target.clientId);
  sendCursor(clientId);
}

function reorderDay(dayIndex: number, orderedClientIds: string[]) {
  const nextOrder = new Map(orderedClientIds.map((id, index) => [id, index + 1]));
  draftItems.value = draftItems.value.map((item) => {
    if (item.dayIndex !== dayIndex) {
      return item;
    }
    const order = nextOrder.get(item.clientId);
    if (!order) {
      return item;
    }
    return {
      ...item,
      sortOrder: order
    };
  });
  dirty.value = true;
  saveSuccess.value = "";
}

function handleAddDay() {
  if (!selectedItinerary.value) {
    return;
  }
  selectedItinerary.value.days = (selectedItinerary.value.days || 1) + 1;
  activeDay.value = selectedItinerary.value.days;
  dirty.value = true;
  saveSuccess.value = "";
}

function patchItem(payload: { clientId: string; patch: TimelineItemPatch }) {
  draftItems.value = draftItems.value.map((item) => {
    if (item.clientId !== payload.clientId) {
      return item;
    }
    return {
      ...item,
      ...payload.patch,
      startTime:
        payload.patch.startTime !== undefined ? normalizeTime(payload.patch.startTime) : item.startTime
    };
  });
  dirty.value = true;
  saveSuccess.value = "";
}

function addItem(payload: AddTimelineBlockPayload) {
  if (!selectedItineraryId.value) {
    saveError.value = "未选中行程，无法添加时间块";
    return;
  }
  saveError.value = "";
  saveSuccess.value = "";
  const dayItems = draftItems.value.filter((item) => item.dayIndex === payload.dayIndex);
  const newItem: TimelineDraftItem = {
    clientId: makeClientId(),
    itemId: null,
    itineraryId: selectedItineraryId.value,
    dayIndex: payload.dayIndex,
    sortOrder: dayItems.length + 1,
    startTime: normalizeTime(payload.startTime),
    durationMinutes: payload.durationMinutes,
    cost: payload.cost,
    tips: payload.tips,
    poi: {
      id: payload.poi.id,
      name: payload.poi.name,
      type: payload.poi.type,
      longitude: payload.poi.longitude,
      latitude: payload.poi.latitude,
      address: payload.poi.address,
      opening_hours: payload.poi.opening_hours,
      ticket_price: payload.poi.ticket_price,
      ticket_rules: payload.poi.ticket_rules || []
    }
  };
  draftItems.value = [...draftItems.value, newItem];
  selectItem(newItem.clientId);
  dirty.value = true;
  saveSuccess.value = "已添加时间块（未保存）";
}

function deleteDraftItem(clientId: string) {
  const target = draftItems.value.find((item) => item.clientId === clientId);
  if (!target) {
    return;
  }
  const remaining = draftItems.value.filter((item) => item.clientId !== clientId);
  const dayItems = remaining
    .filter((item) => item.dayIndex === target.dayIndex)
    .sort((a, b) => a.sortOrder - b.sortOrder)
    .map((item, index) => ({
      ...item,
      sortOrder: index + 1
    }));
  draftItems.value = [...remaining.filter((item) => item.dayIndex !== target.dayIndex), ...dayItems].sort(
    (a, b) => a.dayIndex - b.dayIndex || a.sortOrder - b.sortOrder
  );
  if (activeItemClientId.value === clientId) {
    const fallback = dayItems[0] || draftItems.value[0] || null;
    activeItemClientId.value = fallback ? fallback.clientId : "";
    activeDay.value = fallback ? fallback.dayIndex : target.dayIndex;
  }
  dirty.value = true;
  saveSuccess.value = "";
}

function hasFieldChanges(base: ItineraryItemWithPoi, current: TimelineDraftItem): boolean {
  const poiChanged = current.poi.id !== base.poi.id;
  const timeChanged = normalizeTime(current.startTime) !== normalizeTime(base.start_time);
  const durationChanged = current.durationMinutes !== base.duration_minutes;
  const costChanged = current.cost !== base.cost;
  const tipsChanged = (current.tips || null) !== (base.tips || null);
  return poiChanged || timeChanged || durationChanged || costChanged || tipsChanged;
}

async function loadSelectedItineraryItems() {
  if (!selectedItineraryId.value) {
    stopCollabHistoryPolling();
    baselineItems.value = [];
    draftItems.value = [];
    activeItemClientId.value = "";
    resetDiffState();
    clearMarkers();
    return;
  }
  if (!token.value) {
    stopCollabHistoryPolling();
    disconnect();
    return;
  }
  itineraryLoading.value = true;
  itineraryError.value = "";
  try {
    const payload = await fetchItineraryItemsWithPoi(
      selectedItineraryId.value,
      token.value,
      selectedCollabGrant.value || undefined
    );
    baselineItems.value = payload.items;
    draftItems.value = payload.items.map(toDraftItem);
    const firstItem = draftItems.value[0] || null;
    activeDay.value = firstItem?.dayIndex || 1;
    activeItemClientId.value = firstItem?.clientId || "";
    dirty.value = false;
    saveError.value = "";
    saveSuccess.value = "";
    renderCurrentMarkers();
    if (diffOpen.value) {
      await loadDiffData(true);
    } else {
      resetDiffState(true);
    }
    itineraryStartDateDraft.value = selectedItinerary.value?.start_date || "";
    await loadWeather();
    await loadCollabLinksAndHistory();
    startCollabHistoryPolling();
    connectCollabChannel();
    if (canSaveToServer.value) {
      pushLocalState(currentCollabState(), "bootstrap");
    }
  } catch (e) {
    stopCollabHistoryPolling();
    baselineItems.value = [];
    draftItems.value = [];
    activeItemClientId.value = "";
    resetDiffState();
    clearMarkers();
    weatherItems.value = [];
    weatherError.value = "";
    collabLinks.value = [];
    collabHistory.value = [];
    clearCollabGrant(selectedItineraryId.value);
    disconnect();
    itineraryError.value = e instanceof Error ? e.message : "加载行程地点失败";
  } finally {
    itineraryLoading.value = false;
  }
}

async function loadWeather(forceRefresh = false) {
  if (!token.value || !selectedItineraryId.value) {
    weatherItems.value = [];
    weatherError.value = "";
    return;
  }
  if (!selectedItinerary.value?.start_date) {
    weatherItems.value = [];
    weatherError.value = "";
    return;
  }
  weatherLoading.value = true;
  weatherError.value = "";
  try {
    const payload = await fetchItineraryWeather(
      selectedItineraryId.value,
      token.value,
      forceRefresh,
      selectedCollabGrant.value || undefined
    );
    weatherItems.value = payload.items;
  } catch (e) {
    weatherItems.value = [];
    weatherError.value = e instanceof Error ? e.message : "加载天气失败";
  } finally {
    weatherLoading.value = false;
  }
}

async function loadItineraries() {
  if (!token.value) {
    resetItineraryState();
    return;
  }
  itineraryLoading.value = true;
  itineraryError.value = "";
  try {
    if (typeof route.query.collab_token === "string" && route.query.collab_token.trim()) {
      itineraryError.value = "协作链接已升级为分享码，请到“加入协作”页面输入分享码后进入。";
    }
    const payload = await fetchItineraries(token.value);
    const ownItineraries = payload.items;
    itineraries.value = ownItineraries;

    const queryItineraryId = typeof route.query.itinerary_id === "string" ? route.query.itinerary_id.trim() : "";
    if (queryItineraryId && !ownItineraries.some((item) => item.id === queryItineraryId)) {
      const grantEntry = getCollabGrant(queryItineraryId);
      if (grantEntry?.grant) {
        try {
          const shared = await fetchItineraryById(queryItineraryId, token.value, grantEntry.grant);
          itineraries.value = [shared, ...ownItineraries];
        } catch (e) {
          clearCollabGrant(queryItineraryId);
          itineraryError.value = e instanceof Error ? e.message : "协作授权已失效，请重新输入分享码";
        }
      }
    }

    if (itineraries.value.length === 0) {
      selectedItineraryId.value = "";
      baselineItems.value = [];
      draftItems.value = [];
      activeItemClientId.value = "";
      clearMarkers();
      return;
    }
    const queryExists = queryItineraryId && itineraries.value.some((item) => item.id === queryItineraryId);
    if (queryExists) {
      selectedItineraryId.value = queryItineraryId;
    } else if (!itineraries.value.some((item) => item.id === selectedItineraryId.value)) {
      selectedItineraryId.value = itineraries.value[0].id;
    }
    await loadSelectedItineraryItems();
  } catch (e) {
    resetItineraryState();
    itineraryError.value = e instanceof Error ? e.message : "加载行程失败";
  } finally {
    itineraryLoading.value = false;
  }
}

async function loadPoiCatalog() {
  poiLoading.value = true;
  poiError.value = "";
  try {
    const payload = await fetchPois(token.value || undefined, 0, 100);
    poiCatalog.value = payload.items;
  } catch (e) {
    poiCatalog.value = [];
    poiError.value = e instanceof Error ? e.message : "加载景点列表失败";
  } finally {
    poiLoading.value = false;
  }
}

function queueCollabSync(origin: string) {
  if (applyingRemoteCollab.value) {
    return;
  }
  if (!collabConnected.value || collabPermission.value !== "edit") {
    return;
  }
  if (collabSyncTimer) {
    clearTimeout(collabSyncTimer);
    collabSyncTimer = null;
  }
  collabSyncTimer = setTimeout(() => {
    pushLocalState(currentCollabState(), origin);
    collabSyncTimer = null;
  }, 160);
}

function connectCollabChannel() {
  if (!selectedItineraryId.value) {
    stopCollabDiffTimer();
    disconnect();
    return;
  }
  if (token.value && (canManageCollabLinks.value || Boolean(selectedCollabGrant.value))) {
    connect();
    startCollabDiffTimer();
    return;
  }
  stopCollabDiffTimer();
  disconnect();
}

function stopCollabHistoryPolling() {
  if (collabHistoryPollTimer) {
    clearInterval(collabHistoryPollTimer);
    collabHistoryPollTimer = null;
  }
}

function startCollabHistoryPolling() {
  stopCollabHistoryPolling();
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) {
    return;
  }
  collabHistoryPollTimer = setInterval(() => {
    void loadCollabLinksAndHistory({ silent: true });
  }, COLLAB_HISTORY_POLL_INTERVAL_MS);
}

async function loadCollabLinksAndHistory(options: { silent?: boolean } = {}) {
  const silent = options.silent === true;
  if (!token.value || !selectedItineraryId.value || (!canManageCollabLinks.value && !selectedCollabGrant.value)) {
    stopCollabHistoryPolling();
    collabLinks.value = [];
    collabHistory.value = [];
    collabHistoryLoading.value = false;
    collabHistorySyncing = false;
    return;
  }
  if (collabHistorySyncing) {
    return;
  }
  collabError.value = "";
  collabHistorySyncing = true;
  if (!silent) {
    collabHistoryLoading.value = true;
  }
  try {
    const promises: Promise<void>[] = [];
    if (canManageCollabLinks.value) {
      promises.push(
        fetchCollabLinks(selectedItineraryId.value, token.value).then(res => {
          collabLinks.value = res.items;
        })
      );
    } else {
      collabLinks.value = [];
    }
    promises.push(
      fetchCollabHistory(selectedItineraryId.value, token.value, 0, 20, selectedCollabGrant.value || undefined).then(res => {
        collabHistory.value = res.items;
      })
    );
    await Promise.all(promises);
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "加载协作信息失败";
  } finally {
    collabHistorySyncing = false;
    if (!silent) {
      collabHistoryLoading.value = false;
    }
  }
}

async function handleCreateCollabLink() {
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) {
    return;
  }
  collabCreatePending.value = true;
  collabError.value = "";
  try {
    const result = await createCollabLink(selectedItineraryId.value, token.value, collabPermissionDraft.value);
    collabShareCode.value = result.share_code;
    collabShareUrl.value = result.share_url;
    await navigator.clipboard.writeText(result.share_code);
    saveSuccess.value = "分享码已创建并复制到剪贴板";
    await loadCollabLinksAndHistory();
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "创建协作链接失败";
  } finally {
    collabCreatePending.value = false;
  }
}

async function handleRevokeCollabLink(linkId: string) {
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) {
    return;
  }
  collabError.value = "";
  try {
    await updateCollabLink(selectedItineraryId.value, linkId, token.value, { revoke: true });
    await loadCollabLinksAndHistory();
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "撤销协作链接失败";
  }
}

async function handleToggleCollabLinkPermission(linkId: string, nextPermission: "edit" | "read") {
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) {
    return;
  }
  collabError.value = "";
  try {
    await updateCollabLink(selectedItineraryId.value, linkId, token.value, {
      permission: nextPermission
    });
    await loadCollabLinksAndHistory();
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "更新协作权限失败";
  }
}

async function handleCopyCollabShareCode(shareCode: string) {
  try {
    await navigator.clipboard.writeText(shareCode);
    saveSuccess.value = "分享码已复制";
  } catch {
    collabError.value = "复制失败，请手动复制分享码";
  }
}

async function handleSaveChanges() {
  if (!token.value || !selectedItineraryId.value || !canSaveToServer.value) {
    saveError.value = "当前协作权限不支持保存到服务器";
    return;
  }
  const collabGrant = selectedCollabGrant.value || undefined;
  savePending.value = true;
  saveError.value = "";
  saveSuccess.value = "";

  try {
    const baselineById = new Map(baselineItems.value.map((item) => [item.item_id, item]));
    const currentByItemId = new Map(
      draftItems.value.filter((item) => Boolean(item.itemId)).map((item) => [item.itemId as string, item])
    );

    const deletedIds: string[] = [];
    const movedIds: string[] = [];
    const updatePayloads: Array<{ itemId: string; payload: Partial<ItineraryItemCreatePayload> }> = [];

    for (const base of baselineItems.value) {
      const current = currentByItemId.get(base.item_id);
      if (!current) {
        deletedIds.push(base.item_id);
        continue;
      }
      const daySortChanged = current.dayIndex !== base.day_index || current.sortOrder !== base.sort_order;
      if (daySortChanged) {
        movedIds.push(base.item_id);
        continue;
      }
      if (!hasFieldChanges(base, current)) {
        continue;
      }
      updatePayloads.push({
        itemId: base.item_id,
        payload: {
          poi_id: current.poi.id,
          start_time: normalizeTime(current.startTime),
          duration_minutes: current.durationMinutes,
          cost: current.cost,
          tips: current.tips
        }
      });
    }

    const movedIdSet = new Set(movedIds);
    const createItems = draftItems.value
      .filter((item) => item.itemId === null || (item.itemId && movedIdSet.has(item.itemId)))
      .slice()
      .sort((a, b) => a.dayIndex - b.dayIndex || a.sortOrder - b.sortOrder);

    const deleteIds = [...new Set([...deletedIds, ...movedIds])];

    for (const itemId of deleteIds) {
      await deleteItineraryItem(selectedItineraryId.value, itemId, token.value, collabGrant);
    }

    for (const item of createItems) {
      const created = await createItineraryItem(
        selectedItineraryId.value,
        toCreatePayload(item),
        token.value,
        collabGrant
      );
      if (item.itemId) {
        baselineById.delete(item.itemId);
      }
      item.itemId = created.id;
    }

    for (const entry of updatePayloads) {
      await updateItineraryItem(
        selectedItineraryId.value,
        entry.itemId,
        entry.payload,
        token.value,
        collabGrant
      );
    }

    await loadSelectedItineraryItems();
    if (diffOpen.value) {
      await loadDiffData(true);
    }
    await loadCollabLinksAndHistory();
    diffActionQueue.value = {};
    saveSuccess.value = "已保存时间轴更改";
    dirty.value = false;
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : "保存失败";
    await loadSelectedItineraryItems();
  } finally {
    savePending.value = false;
  }
}

async function handleSaveStartDate() {
  if (!token.value || !selectedItineraryId.value || !canSaveToServer.value) {
    saveError.value = "当前协作权限不支持保存开始日期";
    return;
  }
  savePending.value = true;
  saveError.value = "";
  saveSuccess.value = "";
  try {
    const normalized = itineraryStartDateDraft.value.trim() || null;
    const updated = await updateItinerary(
      selectedItineraryId.value,
      { start_date: normalized },
      token.value,
      selectedCollabGrant.value || undefined
    );
    const target = itineraries.value.find((item) => item.id === selectedItineraryId.value);
    if (target) {
      target.start_date = updated.start_date;
    }
    itineraryStartDateDraft.value = updated.start_date || "";
    saveSuccess.value = "开始日期已保存，正在刷新天气";
    await loadWeather(true);
    saveSuccess.value = "开始日期已保存";
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : "更新开始日期失败";
  } finally {
    savePending.value = false;
  }
}

async function handleCancelChanges() {
  saveError.value = "";
  saveSuccess.value = "";
  await loadSelectedItineraryItems();
  diffActionQueue.value = {};
  if (diffOpen.value) {
    await loadDiffData(true);
  }
}

function openDiscardCurrentItineraryDialog() {
  if (!selectedItineraryId.value || !selectedItinerary.value || !canManageCollabLinks.value) {
    return;
  }
  discardDialogOpen.value = true;
}

function closeDiscardCurrentItineraryDialog() {
  discardDialogOpen.value = false;
}

async function handleDiscardCurrentItinerary() {
  if (!token.value || !selectedItineraryId.value || !selectedItinerary.value || !canManageCollabLinks.value) {
    return;
  }
  savePending.value = true;
  saveError.value = "";
  saveSuccess.value = "";
  try {
    await deleteItinerary(selectedItineraryId.value, token.value);
    await loadItineraries();
    resetDiffState();
    saveSuccess.value = "已作废当前行程";
    closeDiscardCurrentItineraryDialog();
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : "作废行程失败";
  } finally {
    savePending.value = false;
  }
}

async function initWorkspace() {
  mapLoading.value = true;
  mapError.value = "";
  try {
    await nextTick();
    await initMap();
    await Promise.all([loadItineraries(), loadPoiCatalog()]);
  } catch (e) {
    mapError.value = e instanceof Error ? e.message : "地图初始化失败";
  } finally {
    mapLoading.value = false;
  }
}

async function handleAiImported() {
  await loadSelectedItineraryItems();
}

function handleLogout() {
  clearAuth();
  resetItineraryState();
  poiCatalog.value = [];
  poiError.value = "";
  mapError.value = "";
}

watch(
  () => isLoggedIn.value,
  async (value) => {
    if (value) {
      await initWorkspace();
      return;
    }
    destroyMap();
    resetItineraryState();
  }
);

watch(
  () => selectedItineraryId.value,
  async (value, previousValue) => {
    if (!mapReady.value || !value || value === previousValue) {
      return;
    }
    resetDiffState();
    await loadSelectedItineraryItems();
  }
);

watch(
  () => [token.value, selectedItineraryId.value, selectedCollabGrant.value] as const,
  ([nextToken, itineraryId]) => {
    if (nextToken && itineraryId) {
      connectCollabChannel();
      startCollabHistoryPolling();
      return;
    }
    stopCollabHistoryPolling();
    disconnect();
  }
);

watch(
  () => canManageCollabLinks.value,
  (value) => {
    if (value) {
      startCollabHistoryPolling();
      return;
    }
    stopCollabHistoryPolling();
  }
);

watch(
  () => mapReady.value,
  (value) => {
    if (value) {
      renderCurrentMarkers();
    }
  }
);

watch(
  () => draftItems.value,
  () => {
    // Only re-render map markers for local edits, not remote sync updates.
    if (!applyingRemoteCollab.value) {
      renderCurrentMarkers();
    }
    queueCollabSync("draft-items");
  },
  { deep: true }
);

watch(
  () => itineraryStartDateDraft.value,
  () => {
    queueCollabSync("start-date");
  }
);

watch(
  () => collabWsError.value,
  (value) => {
    if (value) {
      collabError.value = value;
    }
  }
);

onMounted(async () => {
  await loadMe();
  if (isLoggedIn.value) {
    await initWorkspace();
  }
});

onBeforeUnmount(() => {
  if (timer) {
    clearInterval(timer);
    timer = null;
  }
  stopCollabHistoryPolling();
  if (collabSyncTimer) {
    clearTimeout(collabSyncTimer);
    collabSyncTimer = null;
  }
  disconnect();
  destroyMap();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">
          Project Atlas
        </p>
        <h1>行程编辑器</h1>
      </div>
      <div
        v-if="isLoggedIn"
        class="user-line"
      >
        <CollabAvatarBar
          v-if="collabConnected"
          :participants="collabParticipants"
          :current-user-id="user?.id || null"
        />
        <span>你好，{{ user?.nickname || "Traveler" }}</span>
        <button
          class="btn ghost"
          :disabled="loading"
          @click="handleLogout"
        >
          退出登录
        </button>
      </div>
    </header>

    <section
      v-if="!isLoggedIn"
      class="auth-shell"
    >
      <h2>登录 / 注册</h2>
      <p class="subtle">
        使用手机号验证码进入地图与时间轴工作台。
      </p>
      <label class="field-label">手机号</label>
      <input
        v-model="phone"
        class="input"
        placeholder="请输入中国大陆手机号"
      >
      <div class="action-row">
        <button
          class="btn"
          :disabled="loading || sendCooldown > 0"
          @click="handleSendCode"
        >
          {{ sendCooldown > 0 ? `${sendCooldown}s 后重试` : "发送验证码" }}
        </button>
      </div>
      <label class="field-label">验证码</label>
      <input
        v-model="code"
        class="input"
        placeholder="请输入 6 位验证码"
      >
      <label class="field-label">昵称（首次注册可选）</label>
      <input
        v-model="nickname"
        class="input"
        placeholder="不填则自动生成"
      >
      <div class="action-row">
        <button
          class="btn primary"
          :disabled="loading"
          @click="handleLogin"
        >
          登录 / 注册
        </button>
      </div>
      <p
        v-if="debugCode"
        class="hint"
      >
        开发模式验证码：{{ debugCode }}
      </p>
      <p
        v-if="authError"
        class="error"
      >
        {{ authError }}
      </p>
    </section>

    <section
      v-else
      class="workspace"
    >
      <aside class="left-panel">
        <div class="panel-card">
          <div class="panel-head">
            <h2>行程选择</h2>
            <button
              class="btn ghost"
              :disabled="itineraryLoading"
              @click="loadItineraries"
            >
              刷新
            </button>
          </div>
          <p
            v-if="itineraryError"
            class="error"
          >
            {{ itineraryError }}
          </p>
          <template v-else>
            <select
              v-model="selectedItineraryId"
              class="input"
              :disabled="itineraryLoading || itineraries.length === 0"
            >
              <option
                v-for="itinerary in itineraries"
                :key="itinerary.id"
                :value="itinerary.id"
              >
                {{ itinerary.title }} · {{ itinerary.destination }}
              </option>
            </select>
            <p
              v-if="itineraries.length === 0"
              class="empty-note"
            >
              当前账号暂无行程，请先创建行程。
            </p>
          </template>
        </div>

        <AiPlanGenerator
          :token="token || ''"
          :itinerary-id="selectedItineraryId"
          :disabled="itineraryLoading || !selectedItineraryId || !token || !canManageCollabLinks"
          @imported="handleAiImported"
        />

        <div class="panel-card save-panel">
          <h2>保存状态</h2>
          <p v-if="selectedItinerary">
            当前行程：{{ selectedItinerary.title }}
          </p>
          <p
            v-if="selectedItinerary?.fork_source_itinerary_id"
            class="subtle"
          >
            派生自 @{{ selectedItinerary.fork_source_author_nickname || "未知作者" }} 的《{{ selectedItinerary.fork_source_title || "未命名行程" }}》
          </p>
          <p
            v-if="isDirty"
            class="subtle"
          >
            你有未保存的更改
          </p>
          <p
            v-else
            class="subtle"
          >
            当前无未保存更改
          </p>
          <p
            v-if="saveError"
            class="error"
          >
            {{ saveError }}
          </p>
          <p
            v-if="saveSuccess"
            class="hint"
          >
            {{ saveSuccess }}
          </p>
          <div class="divider-line" />
          <label class="field-label">开始日期（天气映射基准）</label>
          <input
            v-model="itineraryStartDateDraft"
            class="input"
            type="date"
            :disabled="savePending || !selectedItineraryId || !token || !canSaveToServer"
          >
          <button
            class="btn"
            :disabled="savePending || !selectedItineraryId || !token || !canSaveToServer"
            @click="handleSaveStartDate"
          >
            保存开始日期
          </button>
          <div class="action-row">
            <button
              class="btn"
              :disabled="savePending || !isDirty || !selectedItineraryId || !token || !canSaveToServer"
              @click="handleCancelChanges"
            >
              取消更改
            </button>
            <button
              class="btn primary"
              :disabled="savePending || !isDirty || !selectedItineraryId || !token || !canSaveToServer"
              @click="handleSaveChanges"
            >
              {{ savePending ? "保存中..." : "保存更改" }}
            </button>
            <button
              class="btn ghost"
              :disabled="savePending || !selectedItineraryId || !isForkedItinerary || !token || !canManageCollabLinks"
              @click="toggleDiffPanel"
            >
              {{ diffOpen ? "收起修改对比" : "查看修改对比" }}
            </button>
            <button
              class="btn danger"
              :disabled="savePending || !selectedItineraryId || !token || !canManageCollabLinks"
              @click="openDiscardCurrentItineraryDialog"
            >
              作废当前行程
            </button>
          </div>
          <p
            v-if="!isForkedItinerary && selectedItineraryId"
            class="subtle"
          >
            当前行程不是派生副本，暂无可对比的源快照。
          </p>
        </div>

        <CollabPanel
          v-if="selectedItineraryId"
          v-model:collab-permission-draft="collabPermissionDraft"
          :collab-connected="collabConnected"
          :collab-permission="collabPermission"
          :can-manage-collab-links="canManageCollabLinks"
          :can-save-to-server="canSaveToServer"
          :collab-error="collabError"
          :collab-ws-error="collabWsError"
          :collab-participants="collabParticipants"
          :collab-create-pending="collabCreatePending"
          :selected-itinerary-id="selectedItineraryId"
          :collab-share-code="collabShareCode"
          :collab-share-url="collabShareUrl"
          :collab-links="collabLinks"
          :collab-history-loading="collabHistoryLoading"
          :meaningful-collab-history="meaningfulCollabHistory"
          @create-collab-link="handleCreateCollabLink"
          @copy-share-code="handleCopyCollabShareCode"
          @toggle-link-permission="handleToggleCollabLinkPermission"
          @revoke-link="handleRevokeCollabLink"
        />

        <ItineraryDiffPanel
          :open="diffOpen"
          :loading="diffLoading"
          :error="diffError"
          :diff="diffData"
          :active-day="activeDay"
          :queued-count="Object.keys(diffActionQueue).length"
          :submit-pending="diffSubmitPending"
          :submit-error="diffSubmitError"
          :submit-warnings="diffSubmitWarnings"
          :items="draftItems"
          @jump-to-key="jumpToDiffKey"
          @stage-action="stageDiffAction"
          @submit-actions="submitQueuedDiffActions"
        />
      </aside>

      <section class="editor-panel">
        <TimelineWeatherStrip
          :loading="weatherLoading"
          :error="weatherError"
          :has-start-date="hasStartDate"
          :items="weatherItems"
          @retry="loadWeather(true)"
        />
        <TimelineEditor
          v-if="selectedItinerary"
          :days="selectedItinerary.days"
          :items="draftItems"
          :active-day="activeDay"
          :active-item-client-id="activeItemClientId"
          :remote-cursors="remoteCursors"
          :pois="poiCatalog"
          :poi-loading="poiLoading"
          :poi-error="poiError"
          @update:active-day="activeDay = $event"
          @select-item="selectItem"
          @delete-item="deleteDraftItem"
          @patch-item="patchItem"
          @reorder-day="reorderDay($event.dayIndex, $event.orderedClientIds)"
          @add-item="addItem"
          @add-day="handleAddDay"
        />
        <div
          v-else
          class="panel-card"
        >
          <h2>时间轴编辑器</h2>
          <p class="empty-note">
            当前未选中有效行程，请先在左侧选择行程。
          </p>
        </div>

        <div class="map-frame">
          <div
            ref="mapHost"
            class="map-host"
          />
          <div
            v-if="mapLoading"
            class="overlay"
          >
            地图加载中...
          </div>
          <div
            v-else-if="mapError"
            class="overlay error"
          >
            {{ mapError }}
          </div>
        </div>

        <PoiInfoCard
          v-if="selectedMapItem"
          :item="selectedMapItem"
          :token="token || ''"
          :source-itinerary-id="selectedItineraryId || null"
        />
      </section>
    </section>

    <ConfirmDialog
      :open="discardDialogOpen"
      title="确认作废当前行程"
      :message="`确认作废《${selectedItinerary?.title || '当前行程'}》？作废后无法恢复。`"
      confirm-text="确认作废"
      cancel-text="暂不作废"
      :danger="true"
      :loading="savePending"
      @cancel="closeDiscardCurrentItineraryDialog"
      @confirm="handleDiscardCurrentItinerary"
    />
  </main>
</template>
