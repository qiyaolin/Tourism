<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  autoLayoutBoard,
  createBlockDependency,
  createBlock,
  createCollabLink,
  deleteBlock as apiDeleteBlock,
  fetchBoard,
  fetchCollabHistory,
  fetchCollabLinks,
  fetchItineraries,
  fetchItineraryById,
  fetchItineraryDiff,
  fetchItineraryDiffActionStatuses,
  fetchItineraryWeather,
  forkTemplate,
  migrateLegacyItems,
  publishTemplate,
  rateTemplate,
  submitItineraryDiffActionsBatch,
  ungroupBlock as apiUngroupBlock,
  updateBlock,
  updateBlockLayout,
  updateCollabLink,
  updateItinerary,
  type BlockCreatePayload,
  type BlockDependencyResponse,
  type BlockResponse,
  type BoardLaneSummary,
  type CollabHistoryItem,
  type CollabLinkResponse,
  type ItineraryDiffActionInput,
  type ItineraryDiffResponse,
  type ItineraryResponse,
  type ItineraryItemWithPoi,
  type ItineraryWeatherDayResponse,
  type TemplateApiResponse
} from "../api";
import CollabAvatarBar from "../components/CollabAvatarBar.vue";
import CollabPanel from "../components/CollabPanel.vue";
import ItineraryDiffPanel from "../components/ItineraryDiffPanel.vue";
import TimelineWeatherStrip from "../components/TimelineWeatherStrip.vue";
import BlockEditDrawer from "../components/editor/BlockEditDrawer.vue";
import GroupPublishDialog from "../components/editor/GroupPublishDialog.vue";
import MaterialPanel from "../components/editor/MaterialPanel.vue";
import PreviewPanel from "../components/editor/PreviewPanel.vue";
import TemplateDetailPanel from "../components/editor/TemplateDetailPanel.vue";
import TimelineTrack from "../components/editor/TimelineTrack.vue";
import { useAuth } from "../composables/useAuth";
import { useYjsCollab } from "../composables/useYjsCollab";
import type { Block, BlockDependency, BlockType } from "../types/block";
import { isCnPhone, normalizePhone } from "../utils/validators";

const route = useRoute();
const {
  user,
  loading: authLoading,
  error: authError,
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

const phone = ref("");
const code = ref("");
const nickname = ref("");
const sendCooldown = ref(0);
let sendCodeTimer: ReturnType<typeof setInterval> | null = null;

const itineraries = ref<ItineraryResponse[]>([]);
const selectedItineraryId = ref("");
const itineraryDays = ref(3);
const itineraryLoading = ref(false);
const itineraryError = ref("");

const blocks = ref<Block[]>([]);
const boardDependencies = ref<BlockDependency[]>([]);
const boardLanes = ref<BoardLaneSummary[]>([]);
const activeDay = ref(1);
const activeBlockId = ref("");
const blockLoading = ref(false);
const blockError = ref("");

const savePending = ref(false);
const saveError = ref("");
const saveSuccess = ref("");
const itineraryStartDateDraft = ref("");

const weatherItems = ref<ItineraryWeatherDayResponse[]>([]);
const weatherLoading = ref(false);
const weatherError = ref("");

const editDrawerOpen = ref(false);
const editingBlock = ref<Block | null>(null);
const publishDialogOpen = ref(false);
const selectedBlockIds = ref<Set<string>>(new Set());
const multiSelectMode = ref(false);
const templateDetailOpen = ref(false);
const viewingTemplate = ref<TemplateApiResponse | null>(null);

const diffOpen = ref(false);
const diffLoading = ref(false);
const diffError = ref("");
const diffData = ref<ItineraryDiffResponse | null>(null);
const diffActionQueue = ref<Record<string, ItineraryDiffActionInput>>({});
const diffSubmitPending = ref(false);
const diffSubmitError = ref("");
const diffSubmitWarnings = ref<string[]>([]);

const collabLinks = ref<CollabLinkResponse[]>([]);
const collabHistory = ref<CollabHistoryItem[]>([]);
const collabHistoryLoading = ref(false);
const collabHistorySyncing = ref(false);
const collabError = ref("");
const collabShareCode = ref("");
const collabShareUrl = ref("");
const collabCreatePending = ref(false);
const collabPermissionDraft = ref<"edit" | "read">("edit");

const applyingRemoteCollab = ref(false);
let collabSyncTimer: ReturnType<typeof setTimeout> | null = null;
let collabHistoryPollTimer: ReturnType<typeof setInterval> | null = null;
let collabDiffTimer: ReturnType<typeof setInterval> | null = null;
let lastCollabSnapshotKey = "";
const COLLAB_HISTORY_POLL_INTERVAL_MS = 6000;

const selectedItinerary = computed(
  () => itineraries.value.find((item) => item.id === selectedItineraryId.value) || null
);
const isForkedItinerary = computed(() => Boolean(selectedItinerary.value?.fork_source_itinerary_id));
const hasStartDate = computed(() => Boolean(selectedItinerary.value?.start_date));
const selectedCollabGrantEntry = computed(() => getCollabGrant(selectedItineraryId.value));
const selectedCollabGrant = computed(() => selectedCollabGrantEntry.value?.grant || "");
const canManageCollabLinks = computed(
  () => Boolean(selectedItinerary.value && user.value && selectedItinerary.value.creator_user_id === user.value.id)
);
const canSaveToServer = computed(() => {
  if (!token.value || !selectedItineraryId.value) return false;
  if (canManageCollabLinks.value) return true;
  return selectedCollabGrantEntry.value?.permission === "edit";
});

function findBlockById(tree: Block[], id: string): Block | null {
  for (const block of tree) {
    if (block.id === id) return block;
    if (block.children?.length) {
      const found = findBlockById(block.children, id);
      if (found) return found;
    }
  }
  return null;
}

function flattenBlocks(tree: Block[]): Block[] {
  const result: Block[] = [];
  for (const b of tree) {
    result.push(b);
    if (b.children?.length) result.push(...flattenBlocks(b.children));
  }
  return result;
}

const allBlocks = computed(() => flattenBlocks(blocks.value));
const selectedBlock = computed(() => {
  if (!activeBlockId.value) return null;
  return findBlockById(blocks.value, activeBlockId.value);
});
const selectedBlocksForPublish = computed(() => allBlocks.value.filter((b) => selectedBlockIds.value.has(b.id)));
const meaningfulCollabHistory = computed(() =>
  collabHistory.value.filter((item) => {
    if (item.event_type !== "content_sync" && item.event_type !== "y_update") return false;
    const payload = item.payload || {};
    const description = typeof payload.description === "string" ? payload.description : "";
    return description.includes("[") || description.includes("block");
  })
);
const diffPanelItems = computed(() =>
  allBlocks.value
    .filter((item) => !item.parentBlockId)
    .map((item) => ({ dayIndex: item.dayIndex, sortOrder: item.sortOrder, poi: { name: item.title } }))
);
const mapItems = computed<ItineraryItemWithPoi[]>(() =>
  allBlocks.value
    .filter(
      (item) =>
        !item.isContainer &&
        Number.isFinite(item.longitude) &&
        Number.isFinite(item.latitude)
    )
    .map((item) => ({
      item_id: item.id,
      itinerary_id: item.itineraryId,
      day_index: item.dayIndex,
      sort_order: item.sortOrder,
      start_time: null,
      duration_minutes: item.durationMinutes,
      cost: item.cost,
      tips: item.tips,
      poi: {
        id: item.id,
        name: item.title,
        type: item.blockType,
        longitude: Number(item.longitude),
        latitude: Number(item.latitude),
        address: item.address,
        opening_hours: null,
        ticket_price: null,
        ticket_rules: []
      }
    }))
);
const focusedMapBlockId = computed(() => selectedBlock.value?.id || "");

function mapDependencyResponseToModel(item: BlockDependencyResponse): BlockDependency {
  return {
    id: item.id,
    itineraryId: item.itinerary_id,
    fromBlockId: item.from_block_id,
    toBlockId: item.to_block_id,
    edgeType: item.edge_type,
    createdAt: item.created_at,
  };
}

function mapResponseToBlock(r: BlockResponse): Block {
  return {
    id: r.id,
    itineraryId: r.itinerary_id,
    parentBlockId: r.parent_block_id,
    sortOrder: r.sort_order,
    dayIndex: r.day_index,
    laneKey: r.lane_key || "core",
    startMinute: r.start_minute ?? null,
    endMinute: r.end_minute ?? null,
    blockType: (r.block_type as BlockType) || "scenic",
    title: r.title,
    durationMinutes: r.duration_minutes,
    cost: r.cost,
    tips: r.tips,
    longitude: r.longitude,
    latitude: r.latitude,
    address: r.address,
    photos: r.photos,
    typeData: r.type_data,
    isContainer: r.is_container,
    sourceTemplateId: r.source_template_id,
    status: r.status || "draft",
    priority: r.priority || "medium",
    riskLevel: r.risk_level || "low",
    assigneeUserId: r.assignee_user_id,
    tags: r.tags,
    uiMeta: r.ui_meta,
    children: (r.children || []).map(mapResponseToBlock),
    createdAt: r.created_at,
    updatedAt: r.updated_at
  };
}

function serializeBlock(block: Block): Record<string, unknown> {
  return {
    id: block.id,
    itineraryId: block.itineraryId,
    parentBlockId: block.parentBlockId,
    sortOrder: block.sortOrder,
    dayIndex: block.dayIndex,
    laneKey: block.laneKey,
    startMinute: block.startMinute,
    endMinute: block.endMinute,
    blockType: block.blockType,
    title: block.title,
    durationMinutes: block.durationMinutes,
    cost: block.cost,
    tips: block.tips,
    longitude: block.longitude,
    latitude: block.latitude,
    address: block.address,
    photos: block.photos,
    typeData: block.typeData,
    isContainer: block.isContainer,
    sourceTemplateId: block.sourceTemplateId,
    status: block.status,
    priority: block.priority,
    riskLevel: block.riskLevel,
    assigneeUserId: block.assigneeUserId,
    tags: block.tags,
    uiMeta: block.uiMeta,
    createdAt: block.createdAt,
    updatedAt: block.updatedAt,
    children: (block.children || []).map(serializeBlock)
  };
}

function deserializeBlock(raw: unknown): Block | null {
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const row = raw as Record<string, unknown>;
  if (typeof row.id !== "string" || typeof row.title !== "string") return null;
  const dayIndex = Number(row.dayIndex);
  const sortOrder = Number(row.sortOrder);
  if (!Number.isFinite(dayIndex) || !Number.isFinite(sortOrder)) return null;
  const childrenRaw = Array.isArray(row.children) ? row.children : [];
  const children = childrenRaw.map((item) => deserializeBlock(item)).filter((item): item is Block => item !== null);
  return {
    id: row.id,
    itineraryId: typeof row.itineraryId === "string" ? row.itineraryId : selectedItineraryId.value,
    parentBlockId: typeof row.parentBlockId === "string" ? row.parentBlockId : null,
    sortOrder: Math.max(1, Math.floor(sortOrder)),
    dayIndex: Math.max(1, Math.floor(dayIndex)),
    laneKey: typeof row.laneKey === "string" && row.laneKey.trim() ? row.laneKey : "core",
    startMinute: typeof row.startMinute === "number" ? row.startMinute : null,
    endMinute: typeof row.endMinute === "number" ? row.endMinute : null,
    blockType: typeof row.blockType === "string" ? (row.blockType as BlockType) : "scenic",
    title: row.title,
    durationMinutes: typeof row.durationMinutes === "number" ? row.durationMinutes : null,
    cost: typeof row.cost === "number" ? row.cost : null,
    tips: typeof row.tips === "string" ? row.tips : null,
    longitude: typeof row.longitude === "number" ? row.longitude : null,
    latitude: typeof row.latitude === "number" ? row.latitude : null,
    address: typeof row.address === "string" ? row.address : null,
    photos: Array.isArray(row.photos) ? (row.photos as string[]) : null,
    typeData: row.typeData && typeof row.typeData === "object" && !Array.isArray(row.typeData)
      ? (row.typeData as Record<string, unknown>)
      : null,
    isContainer: Boolean(row.isContainer),
    sourceTemplateId: typeof row.sourceTemplateId === "string" ? row.sourceTemplateId : null,
    status: typeof row.status === "string" ? (row.status as Block["status"]) : "draft",
    priority: typeof row.priority === "string" ? (row.priority as Block["priority"]) : "medium",
    riskLevel: typeof row.riskLevel === "string" ? (row.riskLevel as Block["riskLevel"]) : "low",
    assigneeUserId: typeof row.assigneeUserId === "string" ? row.assigneeUserId : null,
    tags: Array.isArray(row.tags) ? (row.tags.filter((i): i is string => typeof i === "string")) : null,
    uiMeta: row.uiMeta && typeof row.uiMeta === "object" && !Array.isArray(row.uiMeta)
      ? (row.uiMeta as Record<string, unknown>)
      : null,
    children,
    createdAt: typeof row.createdAt === "string" ? row.createdAt : new Date().toISOString(),
    updatedAt: typeof row.updatedAt === "string" ? row.updatedAt : new Date().toISOString()
  };
}

function currentCollabState() {
  return {
    start_date: itineraryStartDateDraft.value || "",
    items: blocks.value.map((item) => serializeBlock(item))
  };
}

function applyRemoteCollabState(state: { start_date: string; items: unknown[] }) {
  applyingRemoteCollab.value = true;
  try {
    itineraryStartDateDraft.value = typeof state.start_date === "string" ? state.start_date : "";
    const parsed = Array.isArray(state.items)
      ? state.items.map((item) => deserializeBlock(item)).filter((item): item is Block => item !== null)
      : [];
    blocks.value = parsed;
    const first = allBlocks.value[0] || null;
    if (first) {
      activeDay.value = first.dayIndex;
      activeBlockId.value = first.id;
    }
    saveSuccess.value = "Synced remote collaboration updates";
    lastCollabSnapshotKey = JSON.stringify(currentCollabState());
  } finally {
    applyingRemoteCollab.value = false;
  }
}

const { participants: collabParticipants, permission: collabPermission, connected: collabConnected, error: collabWsError, connect, disconnect, pushLocalState, sendHistoryUpdate } = useYjsCollab({
  itineraryId: () => selectedItineraryId.value,
  authToken: () => token.value || "",
  collabGrant: () => selectedCollabGrant.value,
  getLocalState: () => currentCollabState(),
  applyRemoteState: (state) => applyRemoteCollabState(state)
});

function startSendCooldown(seconds: number) {
  sendCooldown.value = seconds;
  if (sendCodeTimer) clearInterval(sendCodeTimer);
  sendCodeTimer = setInterval(() => {
    sendCooldown.value -= 1;
    if (sendCooldown.value <= 0) {
      sendCooldown.value = 0;
      if (sendCodeTimer) {
        clearInterval(sendCodeTimer);
        sendCodeTimer = null;
      }
    }
  }, 1000);
}

async function handleSendCode() {
  const normalized = normalizePhone(phone.value);
  if (!isCnPhone(normalized)) return;
  phone.value = normalized;
  const result = await sendLoginCode(normalized);
  startSendCooldown(60);
  if (result.debug_code) code.value = result.debug_code;
}

async function handleLogin() {
  const normalized = normalizePhone(phone.value);
  if (!isCnPhone(normalized)) return;
  phone.value = normalized;
  await loginWithCode(normalized, code.value.trim(), nickname.value.trim());
  await loadMe();
  await loadWorkspace();
}

function handleLogout() {
  clearAuth();
  resetWorkspaceState();
}

function resetDiffState(keepOpen = false) {
  diffLoading.value = false;
  diffError.value = "";
  diffData.value = null;
  diffActionQueue.value = {};
  diffSubmitPending.value = false;
  diffSubmitError.value = "";
  diffSubmitWarnings.value = [];
  if (!keepOpen) diffOpen.value = false;
}

function resetWorkspaceState() {
  itineraries.value = [];
  selectedItineraryId.value = "";
  itineraryDays.value = 3;
  itineraryLoading.value = false;
  itineraryError.value = "";
  blocks.value = [];
  boardDependencies.value = [];
  boardLanes.value = [];
  activeDay.value = 1;
  activeBlockId.value = "";
  blockLoading.value = false;
  blockError.value = "";
  savePending.value = false;
  saveError.value = "";
  saveSuccess.value = "";
  itineraryStartDateDraft.value = "";
  weatherItems.value = [];
  weatherLoading.value = false;
  weatherError.value = "";
  collabLinks.value = [];
  collabHistory.value = [];
  collabHistoryLoading.value = false;
  collabHistorySyncing.value = false;
  collabError.value = "";
  collabShareCode.value = "";
  collabShareUrl.value = "";
  collabCreatePending.value = false;
  selectedBlockIds.value.clear();
  multiSelectMode.value = false;
  editDrawerOpen.value = false;
  editingBlock.value = null;
  templateDetailOpen.value = false;
  viewingTemplate.value = null;
  publishDialogOpen.value = false;
  stopCollabHistoryPolling();
  stopCollabDiffTimer();
  disconnect();
  resetDiffState();
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
    weatherError.value = e instanceof Error ? e.message : "Failed to load weather";
  } finally {
    weatherLoading.value = false;
  }
}

async function loadDiffData(force = false) {
  if (!token.value || !selectedItineraryId.value || !isForkedItinerary.value) {
    resetDiffState();
    return;
  }
  if (!force && diffData.value) return;
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
    for (const item of statuses.items) statusMap[item.diff_key] = item.action;
    diffData.value.action_statuses = { ...diffData.value.action_statuses, ...statusMap };
  } catch (e) {
    diffData.value = null;
    diffError.value = e instanceof Error ? e.message : "Failed to load diff";
  } finally {
    diffLoading.value = false;
  }
}

async function toggleDiffPanel() {
  if (!isForkedItinerary.value) return;
  diffOpen.value = !diffOpen.value;
  if (diffOpen.value) await loadDiffData();
}

function parseItemKey(key: string): { dayIndex: number; sortOrder: number } | null {
  const match = key.match(/^d(\d+)-s(\d+)$/);
  if (!match) return null;
  return { dayIndex: Number(match[1]), sortOrder: Number(match[2]) };
}

function applyMetadataField(field: string, value: unknown) {
  const current = selectedItinerary.value;
  if (!current) return;
  const target = itineraries.value.find((item) => item.id === current.id);
  if (!target) return;
  if (field === "title" && typeof value === "string") target.title = value;
  if (field === "destination" && typeof value === "string") target.destination = value;
  if (field === "days") {
    const days = Number(value);
    if (Number.isFinite(days)) {
      target.days = Math.max(1, Math.floor(days));
      itineraryDays.value = target.days;
    }
  }
  if (field === "status" && typeof value === "string") target.status = value;
  if (field === "visibility" && typeof value === "string") target.visibility = value;
  if (field === "start_date") {
    target.start_date = typeof value === "string" && value.trim() ? value : null;
    itineraryStartDateDraft.value = target.start_date || "";
  }
}

function stageDiffAction(payload: {
  diff_key: string;
  diff_type: ItineraryDiffActionInput["diff_type"];
  action: ItineraryDiffActionInput["action"];
  reason?: string | null;
  field?: string;
  before?: unknown;
  after?: unknown;
}) {
  if (payload.diff_type === "metadata" && payload.field) {
    applyMetadataField(payload.field, payload.action === "applied" ? payload.after : payload.before);
  }
  diffActionQueue.value[payload.diff_key] = {
    diff_key: payload.diff_key,
    diff_type: payload.diff_type,
    action: payload.action,
    reason: payload.reason || null
  };
  if (diffData.value) {
    diffData.value.action_statuses = { ...diffData.value.action_statuses, [payload.diff_key]: payload.action };
  }
}

async function submitQueuedDiffActions() {
  if (!token.value || !selectedItineraryId.value || !diffData.value) return;
  const actions = Object.values(diffActionQueue.value);
  if (actions.length === 0) return;
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
    diffData.value.action_statuses = { ...diffData.value.action_statuses, ...result.action_statuses };
  } catch (e) {
    diffSubmitError.value = e instanceof Error ? e.message : "Failed to submit diff actions";
  } finally {
    diffSubmitPending.value = false;
  }
}

function jumpToDiffKey(itemKey: string) {
  const parsed = parseItemKey(itemKey);
  if (!parsed) return;
  const target = allBlocks.value
    .filter((item) => !item.parentBlockId)
    .find((item) => item.dayIndex === parsed.dayIndex && item.sortOrder === parsed.sortOrder);
  if (!target) return;
  activeDay.value = target.dayIndex;
  activeBlockId.value = target.id;
}

async function loadCollabLinksAndHistory(options: { silent?: boolean } = {}) {
  const silent = options.silent === true;
  if (!token.value || !selectedItineraryId.value || (!canManageCollabLinks.value && !selectedCollabGrant.value)) {
    stopCollabHistoryPolling();
    collabLinks.value = [];
    collabHistory.value = [];
    collabHistoryLoading.value = false;
    collabHistorySyncing.value = false;
    return;
  }
  if (collabHistorySyncing.value) return;
  collabError.value = "";
  collabHistorySyncing.value = true;
  if (!silent) collabHistoryLoading.value = true;
  try {
    const jobs: Promise<void>[] = [];
    if (canManageCollabLinks.value) {
      jobs.push(
        fetchCollabLinks(selectedItineraryId.value, token.value).then((res) => {
          collabLinks.value = res.items;
        })
      );
    } else {
      collabLinks.value = [];
    }
    jobs.push(
      fetchCollabHistory(selectedItineraryId.value, token.value, 0, 20, selectedCollabGrant.value || undefined).then((res) => {
        collabHistory.value = res.items;
      })
    );
    await Promise.all(jobs);
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "Failed to load collaboration data";
  } finally {
    collabHistorySyncing.value = false;
    if (!silent) collabHistoryLoading.value = false;
  }
}

function stopCollabHistoryPolling() {
  if (collabHistoryPollTimer) {
    clearInterval(collabHistoryPollTimer);
    collabHistoryPollTimer = null;
  }
}

function startCollabHistoryPolling() {
  stopCollabHistoryPolling();
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) return;
  collabHistoryPollTimer = setInterval(() => {
    void loadCollabLinksAndHistory({ silent: true });
  }, COLLAB_HISTORY_POLL_INTERVAL_MS);
}

function stopCollabDiffTimer() {
  if (collabDiffTimer) {
    clearInterval(collabDiffTimer);
    collabDiffTimer = null;
  }
}

function startCollabDiffTimer() {
  stopCollabDiffTimer();
  lastCollabSnapshotKey = JSON.stringify(currentCollabState());
  collabDiffTimer = setInterval(() => {
    if (collabPermission.value !== "edit") return;
    const nextKey = JSON.stringify(currentCollabState());
    if (nextKey === lastCollabSnapshotKey) return;
    lastCollabSnapshotKey = nextKey;
    sendHistoryUpdate("Updated block editor content");
  }, 10000);
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

function queueCollabSync(origin: string) {
  if (applyingRemoteCollab.value) return;
  if (!collabConnected.value || collabPermission.value !== "edit") return;
  if (collabSyncTimer) clearTimeout(collabSyncTimer);
  collabSyncTimer = setTimeout(() => {
    pushLocalState(currentCollabState(), origin);
    collabSyncTimer = null;
  }, 180);
}

async function handleCreateCollabLink() {
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) return;
  collabCreatePending.value = true;
  collabError.value = "";
  try {
    const result = await createCollabLink(selectedItineraryId.value, token.value, collabPermissionDraft.value);
    collabShareCode.value = result.share_code;
    collabShareUrl.value = result.share_url;
    await navigator.clipboard.writeText(result.share_code);
    saveSuccess.value = "Share code copied";
    await loadCollabLinksAndHistory();
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "Failed to create share code";
  } finally {
    collabCreatePending.value = false;
  }
}

async function handleRevokeCollabLink(linkId: string) {
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) return;
  try {
    await updateCollabLink(selectedItineraryId.value, linkId, token.value, { revoke: true });
    await loadCollabLinksAndHistory();
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "Failed to revoke share code";
  }
}

async function handleToggleCollabLinkPermission(linkId: string, nextPermission: "edit" | "read") {
  if (!token.value || !selectedItineraryId.value || !canManageCollabLinks.value) return;
  try {
    await updateCollabLink(selectedItineraryId.value, linkId, token.value, { permission: nextPermission });
    await loadCollabLinksAndHistory();
  } catch (e) {
    collabError.value = e instanceof Error ? e.message : "Failed to update permission";
  }
}

async function handleCopyCollabShareCode(shareCode: string) {
  try {
    await navigator.clipboard.writeText(shareCode);
    saveSuccess.value = "Share code copied";
  } catch {
    collabError.value = "Copy failed";
  }
}

async function handleSaveStartDate() {
  if (!token.value || !selectedItineraryId.value || !canSaveToServer.value) {
    saveError.value = "Read-only collaboration mode";
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
    if (target) target.start_date = updated.start_date;
    itineraryStartDateDraft.value = updated.start_date || "";
    await loadWeather(true);
    saveSuccess.value = "Start date saved";
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : "Failed to save start date";
  } finally {
    savePending.value = false;
  }
}

function ensureCanEdit(): boolean {
  if (!canSaveToServer.value) {
    saveError.value = "Read-only collaboration mode";
    return false;
  }
  return true;
}

async function loadBlocks() {
  if (!token.value || !selectedItineraryId.value) return;
  blockLoading.value = true;
  blockError.value = "";
  try {
    let board = await fetchBoard(selectedItineraryId.value, token.value, selectedCollabGrant.value || undefined);
    if (board.items.length === 0) {
      await migrateLegacyItems(selectedItineraryId.value, token.value, selectedCollabGrant.value || undefined);
      board = await fetchBoard(selectedItineraryId.value, token.value, selectedCollabGrant.value || undefined);
    }
    blocks.value = board.items.map(mapResponseToBlock);
    boardDependencies.value = board.dependencies.map(mapDependencyResponseToModel);
    boardLanes.value = board.lanes;
    const itinerary = itineraries.value.find((item) => item.id === selectedItineraryId.value);
    if (itinerary) {
      itineraryDays.value = itinerary.days;
      itineraryStartDateDraft.value = itinerary.start_date || "";
    }
    const first = allBlocks.value[0] || null;
    activeDay.value = first?.dayIndex || 1;
    activeBlockId.value = first?.id || "";
    if (diffOpen.value) await loadDiffData(true);
    await Promise.all([loadWeather(), loadCollabLinksAndHistory()]);
    startCollabHistoryPolling();
    connectCollabChannel();
    if (canSaveToServer.value) pushLocalState(currentCollabState(), "bootstrap");
  } catch (e) {
    blocks.value = [];
    boardDependencies.value = [];
    boardLanes.value = [];
    blockError.value = e instanceof Error ? e.message : "Failed to load blocks";
  } finally {
    blockLoading.value = false;
  }
}

async function loadItinerariesList() {
  if (!token.value) {
    resetWorkspaceState();
    return;
  }
  itineraryLoading.value = true;
  itineraryError.value = "";
  try {
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
          itineraryError.value = e instanceof Error ? e.message : "Collab grant expired";
        }
      }
    }
    if (itineraries.value.length === 0) {
      selectedItineraryId.value = "";
      blocks.value = [];
      return;
    }
    const queryExists = queryItineraryId && itineraries.value.some((item) => item.id === queryItineraryId);
    if (queryExists) selectedItineraryId.value = queryItineraryId;
    else if (!itineraries.value.some((item) => item.id === selectedItineraryId.value)) selectedItineraryId.value = itineraries.value[0].id;
    await loadBlocks();
  } catch (e) {
    resetWorkspaceState();
    itineraryError.value = e instanceof Error ? e.message : "Failed to load itineraries";
  } finally {
    itineraryLoading.value = false;
  }
}

async function loadWorkspace() {
  await loadItinerariesList();
}

function toggleMultiSelect() {
  multiSelectMode.value = !multiSelectMode.value;
  if (!multiSelectMode.value) selectedBlockIds.value.clear();
}

function handleSelectBlock(block: Block) {
  if (multiSelectMode.value) {
    if (selectedBlockIds.value.has(block.id)) selectedBlockIds.value.delete(block.id);
    else selectedBlockIds.value.add(block.id);
  }
  activeBlockId.value = block.id;
  activeDay.value = block.dayIndex;
}

function handleEditBlock(block: Block) {
  if (!ensureCanEdit()) return;
  editingBlock.value = block;
  editDrawerOpen.value = true;
}

function openNewBlockDrawer() {
  if (!ensureCanEdit()) return;
  editingBlock.value = null;
  editDrawerOpen.value = true;
}

async function handleSaveBlock(data: Record<string, unknown>) {
  if (!token.value || !selectedItineraryId.value || !ensureCanEdit()) return;
  try {
    if (editingBlock.value) {
      const payload: BlockCreatePayload = {
        block_type: String(data.blockType || editingBlock.value.blockType),
        title: String(data.title || editingBlock.value.title),
        day_index: Number(data.dayIndex || editingBlock.value.dayIndex),
        lane_key: String(data.laneKey || editingBlock.value.laneKey || "core"),
        sort_order: Number(data.sortOrder || editingBlock.value.sortOrder),
        start_minute: (data.startMinute as number | null) ?? editingBlock.value.startMinute ?? null,
        end_minute: (data.endMinute as number | null) ?? editingBlock.value.endMinute ?? null,
        duration_minutes: (data.durationMinutes as number | null) ?? null,
        cost: (data.cost as number | null) ?? null,
        tips: (data.tips as string | null) ?? null,
        address: (data.address as string | null) ?? null,
        is_container: Boolean(data.isContainer),
        type_data: (data.typeData as Record<string, unknown> | null) ?? null,
        status: String(data.status || editingBlock.value.status) as "draft" | "ready" | "running" | "done" | "blocked",
        priority: String(data.priority || editingBlock.value.priority) as "low" | "medium" | "high",
        risk_level: String(data.riskLevel || editingBlock.value.riskLevel) as "low" | "medium" | "high",
      };
      await updateBlock(editingBlock.value.id, payload, token.value, selectedCollabGrant.value || undefined);
    } else {
      const payload: BlockCreatePayload = {
        block_type: String(data.blockType || "scenic"),
        title: String(data.title || ""),
        day_index: activeDay.value,
        lane_key: String(data.laneKey || selectedBlock.value?.laneKey || "core"),
        sort_order: allBlocks.value.filter((item) => item.dayIndex === activeDay.value && !item.parentBlockId).length + 1,
        start_minute: (data.startMinute as number | null) ?? null,
        end_minute: (data.endMinute as number | null) ?? null,
        duration_minutes: data.durationMinutes as number | null,
        cost: data.cost as number | null,
        tips: data.tips as string | null,
        address: data.address as string | null,
        is_container: data.isContainer as boolean,
        type_data: data.typeData as Record<string, unknown> | null,
        status: String(data.status || "draft") as "draft" | "ready" | "running" | "done" | "blocked",
        priority: String(data.priority || "medium") as "low" | "medium" | "high",
        risk_level: String(data.riskLevel || "low") as "low" | "medium" | "high"
      };
      await createBlock(selectedItineraryId.value, payload, token.value, selectedCollabGrant.value || undefined);
    }
    editDrawerOpen.value = false;
    editingBlock.value = null;
    await loadBlocks();
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to save block";
  }
}

async function handleDeleteBlock(block: Block) {
  if (!token.value || !ensureCanEdit()) return;
  if (!confirm(`Delete block "${block.title}"?`)) return;
  try {
    await apiDeleteBlock(block.id, token.value, selectedCollabGrant.value || undefined);
    if (activeBlockId.value === block.id) activeBlockId.value = "";
    await loadBlocks();
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to delete block";
  }
}

async function handleUngroupBlock(block: Block) {
  if (!token.value || !ensureCanEdit()) return;
  try {
    await apiUngroupBlock(block.id, token.value, selectedCollabGrant.value || undefined);
    await loadBlocks();
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to ungroup block";
  }
}

async function handleTemplateDrop(data: { template: unknown; dayIndex: number; sortOrder: number; laneKey?: string }) {
  if (!token.value || !selectedItineraryId.value || !ensureCanEdit()) return;
  const template = data.template as TemplateApiResponse;
  try {
    await forkTemplate(
      template.id,
      {
        itinerary_id: selectedItineraryId.value,
        day_index: data.dayIndex,
        sort_order: data.sortOrder,
        lane_key: data.laneKey || selectedBlock.value?.laneKey || "core",
      },
      token.value,
      selectedCollabGrant.value || undefined
    );
    await loadBlocks();
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to add template";
  }
}

async function handleMoveBlockLayout(payload: { blockId: string; dayIndex: number; laneKey: string }) {
  if (!token.value || !selectedItineraryId.value || !ensureCanEdit()) return;
  try {
    await updateBlockLayout(
      payload.blockId,
      {
        day_index: payload.dayIndex,
        lane_key: payload.laneKey,
      },
      token.value,
      selectedCollabGrant.value || undefined
    );
    await loadBlocks();
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to update block layout";
  }
}

async function handleCreateDependency(payload: { fromBlockId: string; toBlockId: string; edgeType: "hard" | "soft" }) {
  if (!token.value || !selectedItineraryId.value || !ensureCanEdit()) return;
  try {
    await createBlockDependency(
      selectedItineraryId.value,
      payload.fromBlockId,
      { to_block_id: payload.toBlockId, edge_type: payload.edgeType },
      token.value,
      selectedCollabGrant.value || undefined
    );
    await loadBlocks();
    saveSuccess.value = "依赖关系已建立";
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to create dependency";
  }
}

async function handleAutoLayoutBoard() {
  if (!token.value || !selectedItineraryId.value || !ensureCanEdit()) return;
  try {
    const result = await autoLayoutBoard(
      selectedItineraryId.value,
      token.value,
      selectedCollabGrant.value || undefined
    );
    await loadBlocks();
    saveSuccess.value = `已自动排布 ${result.updated_count} 个节点`;
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to auto layout board";
  }
}

function openPublishDialog() {
  if (!ensureCanEdit()) return;
  if (selectedBlocksForPublish.value.length === 0 && selectedBlock.value) selectedBlockIds.value.add(selectedBlock.value.id);
  if (selectedBlocksForPublish.value.length === 0) {
    blockError.value = "Select blocks first";
    return;
  }
  publishDialogOpen.value = true;
}

async function handlePublish(data: {
  title: string;
  description: string | null;
  styleTags: string[];
  blockType: string;
  isGroup: boolean;
  contentSnapshot: Record<string, unknown> | null;
  childrenSnapshot: Record<string, unknown>[] | null;
  regionName: string | null;
}) {
  if (!token.value || !ensureCanEdit()) return;
  try {
    await publishTemplate(
      {
        title: data.title,
        description: data.description,
        style_tags: data.styleTags,
        block_type: data.blockType,
        is_group: data.isGroup,
        content_snapshot: data.contentSnapshot,
        children_snapshot: data.childrenSnapshot,
        region_name: data.regionName
      },
      token.value,
      selectedCollabGrant.value || undefined
    );
    publishDialogOpen.value = false;
    selectedBlockIds.value.clear();
    multiSelectMode.value = false;
    saveSuccess.value = "Template published";
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to publish template";
  }
}

function handleSelectTemplate(template: TemplateApiResponse) {
  viewingTemplate.value = template;
  templateDetailOpen.value = true;
}

async function handleRateTemplate(data: { score: number; comment: string | null }) {
  if (!token.value || !viewingTemplate.value) return;
  try {
    await rateTemplate(viewingTemplate.value.id, data, token.value, selectedCollabGrant.value || undefined);
    templateDetailOpen.value = false;
    saveSuccess.value = "Template rated";
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to rate template";
  }
}

async function handleForkFromDetail() {
  if (!token.value || !selectedItineraryId.value || !viewingTemplate.value || !ensureCanEdit()) return;
  try {
    await forkTemplate(
      viewingTemplate.value.id,
      {
        itinerary_id: selectedItineraryId.value,
        day_index: activeDay.value,
        sort_order: allBlocks.value.filter((item) => item.dayIndex === activeDay.value && !item.parentBlockId).length + 1,
        lane_key: selectedBlock.value?.laneKey || "core",
      },
      token.value,
      selectedCollabGrant.value || undefined
    );
    templateDetailOpen.value = false;
    await loadBlocks();
  } catch (e) {
    blockError.value = e instanceof Error ? e.message : "Failed to fork template";
  }
}

watch(
  () => isLoggedIn.value,
  async (value) => {
    if (value) await loadWorkspace();
    else resetWorkspaceState();
  }
);

watch(
  () => selectedItineraryId.value,
  async (value, previousValue) => {
    if (!value || value === previousValue || !token.value) return;
    resetDiffState();
    await loadBlocks();
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
    if (value) startCollabHistoryPolling();
    else stopCollabHistoryPolling();
  }
);

watch(
  () => collabWsError.value,
  (value) => {
    if (value) collabError.value = value;
  }
);

watch(
  () => blocks.value,
  () => {
    queueCollabSync("blocks");
  },
  { deep: true }
);

watch(
  () => itineraryStartDateDraft.value,
  () => {
    queueCollabSync("start-date");
  }
);

onMounted(async () => {
  await loadMe();
  if (isLoggedIn.value) await loadWorkspace();
});

onBeforeUnmount(() => {
  if (sendCodeTimer) {
    clearInterval(sendCodeTimer);
    sendCodeTimer = null;
  }
  stopCollabHistoryPolling();
  stopCollabDiffTimer();
  if (collabSyncTimer) {
    clearTimeout(collabSyncTimer);
    collabSyncTimer = null;
  }
  disconnect();
});
</script>

<template>
  <div v-if="!isLoggedIn" class="login-overlay">
    <div class="login-card">
      <h2>Editor V2</h2>
      <input v-model="phone" placeholder="Phone" class="login-input" />
      <div class="login-row">
        <input v-model="code" placeholder="Code" class="login-input" />
        <button class="btn small" :disabled="authLoading || sendCooldown > 0" @click="handleSendCode">
          {{ sendCooldown > 0 ? `${sendCooldown}s` : "Send" }}
        </button>
      </div>
      <input v-model="nickname" placeholder="Nickname (optional)" class="login-input" />
      <button class="btn primary block" :disabled="authLoading" @click="handleLogin">Login</button>
      <p v-if="debugCode" class="hint">Debug code: {{ debugCode }}</p>
      <p v-if="authError" class="error">{{ authError }}</p>
    </div>
  </div>

  <div v-else class="editor-v2">
    <header class="topbar">
      <div class="topbar-left">
        <strong>Atlas V2</strong>
        <select v-model="selectedItineraryId" class="input select" :disabled="itineraryLoading || itineraries.length === 0">
          <option value="" disabled>选择行程</option>
          <option v-for="item in itineraries" :key="item.id" :value="item.id">
            {{ item.title }} ({{ item.destination }}, {{ item.days }}d)
          </option>
        </select>
        <button class="btn small" :disabled="itineraryLoading" @click="loadItinerariesList">刷新</button>
      </div>
      <div class="topbar-right">
        <CollabAvatarBar v-if="collabConnected" :participants="collabParticipants" :current-user-id="user?.id || null" />
        <span class="subtle">{{ user?.nickname || "旅行者" }}</span>
        <button class="btn small" :class="{ active: multiSelectMode }" @click="toggleMultiSelect">{{ multiSelectMode ? "完成" : "多选" }}</button>
        <button class="btn small" :disabled="!canSaveToServer" @click="openNewBlockDrawer">新建节点</button>
        <button class="btn small" :disabled="authLoading" @click="handleLogout">退出</button>
      </div>
    </header>

    <p v-if="itineraryError" class="error-banner">{{ itineraryError }}</p>
    <p v-if="blockError" class="error-banner">{{ blockError }}</p>

    <section class="workspace">
      <aside class="panel material">
        <MaterialPanel :token="token" @select-template="handleSelectTemplate" />
        <TemplateDetailPanel :template="viewingTemplate" :open="templateDetailOpen" @close="templateDetailOpen = false" @rate="handleRateTemplate" @fork="handleForkFromDetail" />
      </aside>

      <main class="panel main-canvas">
        <TimelineWeatherStrip :loading="weatherLoading" :error="weatherError" :has-start-date="hasStartDate" :items="weatherItems" @retry="loadWeather(true)" />

        <section class="canvas-shell">
          <div class="canvas-head">
            <div>
              <h2>流程编辑画板</h2>
              <p class="subtle">主工作区：按天与泳道组织流程，支持拖拽调度与依赖关系编排。</p>
            </div>
            <div class="row">
              <button class="btn small" :disabled="!canSaveToServer" @click="handleAutoLayoutBoard">自动排布</button>
              <button class="btn small" :disabled="!canSaveToServer" @click="openNewBlockDrawer">新增节点</button>
            </div>
          </div>

          <TimelineTrack
            :blocks="allBlocks"
            :dependencies="boardDependencies"
            :lanes="boardLanes"
            :days="itineraryDays"
            :active-day="activeDay"
            :active-block-id="activeBlockId"
            @update:active-day="activeDay = $event"
            @select-block="handleSelectBlock"
            @edit-block="handleEditBlock"
            @delete-block="handleDeleteBlock"
            @ungroup-block="handleUngroupBlock"
            @drop="handleTemplateDrop"
            @move-block-layout="handleMoveBlockLayout"
            @create-dependency="handleCreateDependency"
          />
        </section>

        <section v-if="selectedItineraryId" class="panel minimap-float">
          <header class="minimap-head">
            <h3>地图小窗</h3>
            <p class="subtle">仅用于选中节点定位，不干扰画板编辑。</p>
          </header>
          <PreviewPanel
            :selected-block="selectedBlock"
            :map-items="mapItems"
            :focused-block-id="focusedMapBlockId"
            :map-loading="blockLoading"
          />
        </section>
      </main>

      <aside class="panel side">
        <section class="card">
          <h3>保存与版本</h3>
          <p class="subtle">节点编辑实时保存，可在此处理起始日期与差异。</p>
          <label class="subtle">开始日期</label>
          <input v-model="itineraryStartDateDraft" class="input" type="date" :disabled="savePending || !selectedItineraryId || !token || !canSaveToServer" />
          <div class="row">
            <button class="btn small" :disabled="savePending || !selectedItineraryId || !token || !canSaveToServer" @click="handleSaveStartDate">保存日期</button>
            <button class="btn small" :disabled="savePending || !selectedItineraryId || !isForkedItinerary || !token || !canManageCollabLinks" @click="toggleDiffPanel">
              {{ diffOpen ? "收起 Diff" : "查看 Diff" }}
            </button>
            <button class="btn small" :disabled="!canSaveToServer" @click="openPublishDialog">发布模板</button>
          </div>
          <p v-if="saveError" class="error">{{ saveError }}</p>
          <p v-if="saveSuccess" class="hint">{{ saveSuccess }}</p>
        </section>

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
          :items="diffPanelItems"
          @jump-to-key="jumpToDiffKey"
          @stage-action="stageDiffAction"
          @submit-actions="submitQueuedDiffActions"
        />
      </aside>
    </section>

    <BlockEditDrawer :block="editingBlock" :open="editDrawerOpen" @close="editDrawerOpen = false" @save="handleSaveBlock" />
    <GroupPublishDialog :open="publishDialogOpen" :selected-blocks="selectedBlocksForPublish" @close="publishDialogOpen = false" @publish="handlePublish" />
  </div>
</template>

<style scoped>
.editor-v2 {
  --surface-root: #090f1d;
  --surface-panel: #121a2b;
  --surface-canvas: #0d1629;
  --surface-card: #19253d;
  --surface-overlay: rgba(8, 14, 25, 0.95);
  --line-soft: rgba(183, 206, 242, 0.2);
  --line-strong: rgba(183, 206, 242, 0.35);
  --text-main: #ecf3ff;
  --text-subtle: #a9c1e8;
  --text-danger: #ffb5b5;
  --accent: #5ec6ff;

  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: radial-gradient(circle at 20% 0%, #122747 0%, var(--surface-root) 48%);
  color: var(--text-main);
  font-family: "Noto Sans SC", "IBM Plex Sans", "Segoe UI", sans-serif;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px;
  border-bottom: 1px solid var(--line-soft);
  gap: 10px;
  background: rgba(9, 15, 29, 0.92);
}

.topbar-left,
.topbar-right,
.row,
.login-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.workspace {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 300px 1fr 380px;
  gap: 12px;
  padding: 12px;
}

.panel {
  min-height: 0;
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  overflow: hidden;
  background: var(--surface-panel);
}

.material {
  background: linear-gradient(180deg, #13213a 0%, #101a2d 100%);
}

.main-canvas {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  background: linear-gradient(180deg, #132441 0%, var(--surface-canvas) 60%);
}

.canvas-shell {
  flex: 1;
  min-height: 420px;
  border: 1px solid var(--line-soft);
  border-radius: 10px;
  background: rgba(12, 20, 35, 0.96);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.canvas-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--line-soft);
}

.canvas-head h2 {
  margin: 0;
  font-size: 16px;
  line-height: 1.2;
  color: #f2f7ff;
}

.canvas-shell :deep(.timeline-track) {
  flex: 1;
  min-height: 0;
  max-height: none;
  border-top: none;
  background: transparent;
}

.canvas-shell :deep(.timeline-track__row) {
  height: 100%;
  min-height: 0;
}

.minimap-float {
  position: absolute;
  right: 14px;
  bottom: 14px;
  width: 340px;
  height: 270px;
  z-index: 10;
  border-color: var(--line-strong);
  background: var(--surface-overlay);
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.4);
}

.minimap-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--line-soft);
  background: rgba(17, 31, 54, 0.95);
}

.minimap-head h3 {
  margin: 0;
  font-size: 13px;
  color: #f2f7ff;
}

.side {
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 10px;
  background: linear-gradient(180deg, #111f36 0%, #101a2b 100%);
}

.card {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  padding: 10px;
  background: var(--surface-card);
}

.input {
  width: 100%;
  box-sizing: border-box;
  padding: 7px 8px;
  border-radius: 8px;
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.07);
  color: var(--text-main);
}

.select {
  min-width: 240px;
}

.btn {
  border: 1px solid var(--line-soft);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
  padding: 7px 10px;
  cursor: pointer;
}

.btn.small {
  padding: 6px 9px;
  font-size: 12px;
}

.btn.primary {
  background: #2f6df6;
  border-color: #2f6df6;
}

.btn.block {
  width: 100%;
}

.btn.active {
  border-color: var(--accent);
  color: var(--accent);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.subtle {
  font-size: 12px;
  color: var(--text-subtle);
  margin: 0;
}

.hint {
  font-size: 12px;
  color: #7cd992;
}

.error {
  font-size: 12px;
  color: var(--text-danger);
}

.error-banner {
  margin: 10px 12px 0;
  padding: 8px 10px;
  border: 1px solid rgba(255, 138, 138, 0.65);
  background: rgba(255, 120, 120, 0.2);
  border-radius: 8px;
}

.login-overlay {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 100vh;
}

.login-card {
  width: 360px;
  max-width: calc(100vw - 24px);
  border: 1px solid var(--line-soft);
  border-radius: 12px;
  padding: 16px;
  background: #111b2f;
}

.login-input {
  width: 100%;
  box-sizing: border-box;
  padding: 8px;
  border-radius: 8px;
  border: 1px solid var(--line-soft);
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
}

@media (max-width: 1400px) {
  .workspace {
    grid-template-columns: 260px 1fr 340px;
  }

  .minimap-float {
    width: 300px;
    height: 250px;
  }
}

@media (max-width: 1200px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .main-canvas {
    min-height: 560px;
  }

  .minimap-float {
    position: static;
    width: 100%;
    height: 260px;
    margin-top: 8px;
  }

  .canvas-shell {
    min-height: 360px;
  }
}
</style>
