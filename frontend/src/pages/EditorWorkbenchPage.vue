<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import {
  createItineraryItem,
  deleteItinerary,
  deleteItineraryItem,
  fetchItineraries,
  fetchItineraryDiff,
  fetchItineraryItemsWithPoi,
  fetchPois,
  updateItineraryItem,
  type ItineraryDiffResponse,
  type ItineraryItemCreatePayload,
  type ItineraryItemWithPoi,
  type ItineraryResponse,
  type PoiResponse
} from "../api";
import AiPlanGenerator from "../components/AiPlanGenerator.vue";
import ConfirmDialog from "../components/ConfirmDialog.vue";
import ItineraryDiffPanel from "../components/ItineraryDiffPanel.vue";
import PoiInfoCard from "../components/PoiInfoCard.vue";
import TimelineEditor from "../components/TimelineEditor.vue";
import { useAmap } from "../composables/useAmap";
import { useAuth } from "../composables/useAuth";
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
  loadMe
} = useAuth();

const { mapReady, initMap, renderMarkers, focusMarker, clearMarkers, destroyMap } = useAmap(mapHost);

const selectedItinerary = computed(
  () => itineraries.value.find((item) => item.id === selectedItineraryId.value) || null
);
const authError = computed(() => error.value);
const isDirty = computed(() => dirty.value && !savePending.value);
const isForkedItinerary = computed(() => Boolean(selectedItinerary.value?.fork_source_itinerary_id));

const selectedMapItem = computed<ItineraryItemWithPoi | null>(() => {
  const target = draftItems.value.find((item) => item.clientId === activeItemClientId.value);
  if (!target) {
    return null;
  }
  return toMapItem(target);
});

let timer: ReturnType<typeof setInterval> | null = null;

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

function resetItineraryState() {
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
  markerKeyToClientId.clear();
  clearMarkers();
}

function resetDiffState(keepOpen = false) {
  diffLoading.value = false;
  diffError.value = "";
  diffData.value = null;
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
      ticket_price: payload.poi.ticket_price
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
  if (!token.value || !selectedItineraryId.value) {
    baselineItems.value = [];
    draftItems.value = [];
    activeItemClientId.value = "";
    resetDiffState();
    clearMarkers();
    return;
  }
  itineraryLoading.value = true;
  itineraryError.value = "";
  try {
    const payload = await fetchItineraryItemsWithPoi(selectedItineraryId.value, token.value);
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
  } catch (e) {
    baselineItems.value = [];
    draftItems.value = [];
    activeItemClientId.value = "";
    resetDiffState();
    clearMarkers();
    itineraryError.value = e instanceof Error ? e.message : "加载行程地点失败";
  } finally {
    itineraryLoading.value = false;
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
    const payload = await fetchItineraries(token.value);
    itineraries.value = payload.items;
    if (itineraries.value.length === 0) {
      selectedItineraryId.value = "";
      baselineItems.value = [];
      draftItems.value = [];
      activeItemClientId.value = "";
      clearMarkers();
      return;
    }
    const queryItineraryId = typeof route.query.itinerary_id === "string" ? route.query.itinerary_id.trim() : "";
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

async function handleSaveChanges() {
  if (!token.value || !selectedItineraryId.value) {
    return;
  }
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
      await deleteItineraryItem(selectedItineraryId.value, itemId, token.value);
    }

    for (const item of createItems) {
      const created = await createItineraryItem(selectedItineraryId.value, toCreatePayload(item), token.value);
      if (item.itemId) {
        baselineById.delete(item.itemId);
      }
      item.itemId = created.id;
    }

    for (const entry of updatePayloads) {
      await updateItineraryItem(selectedItineraryId.value, entry.itemId, entry.payload, token.value);
    }

    await loadSelectedItineraryItems();
    if (diffOpen.value) {
      await loadDiffData(true);
    }
    saveSuccess.value = "已保存时间轴更改";
    dirty.value = false;
  } catch (e) {
    saveError.value = e instanceof Error ? e.message : "保存失败";
    await loadSelectedItineraryItems();
  } finally {
    savePending.value = false;
  }
}

async function handleCancelChanges() {
  saveError.value = "";
  saveSuccess.value = "";
  await loadSelectedItineraryItems();
  if (diffOpen.value) {
    await loadDiffData(true);
  }
}

function openDiscardCurrentItineraryDialog() {
  if (!selectedItineraryId.value || !selectedItinerary.value) {
    return;
  }
  discardDialogOpen.value = true;
}

function closeDiscardCurrentItineraryDialog() {
  discardDialogOpen.value = false;
}

async function handleDiscardCurrentItinerary() {
  if (!token.value || !selectedItineraryId.value || !selectedItinerary.value) {
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
    renderCurrentMarkers();
  },
  { deep: true }
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
        <h1>Phase 1.5 时间轴编辑器</h1>
      </div>
      <div
        v-if="isLoggedIn"
        class="user-line"
      >
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
          :disabled="itineraryLoading || !selectedItineraryId"
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
          <div class="action-row">
            <button
              class="btn"
              :disabled="savePending || !isDirty || !selectedItineraryId"
              @click="handleCancelChanges"
            >
              取消更改
            </button>
            <button
              class="btn primary"
              :disabled="savePending || !isDirty || !selectedItineraryId"
              @click="handleSaveChanges"
            >
              {{ savePending ? "保存中..." : "保存更改" }}
            </button>
            <button
              class="btn ghost"
              :disabled="savePending || !selectedItineraryId || !isForkedItinerary"
              @click="toggleDiffPanel"
            >
              {{ diffOpen ? "收起修改对比" : "查看修改对比" }}
            </button>
            <button
              class="btn danger"
              :disabled="savePending || !selectedItineraryId"
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

        <ItineraryDiffPanel
          :open="diffOpen"
          :loading="diffLoading"
          :error="diffError"
          :diff="diffData"
        />
      </aside>

      <section class="editor-panel">
        <TimelineEditor
          v-if="selectedItinerary"
          :days="selectedItinerary.days"
          :items="draftItems"
          :active-day="activeDay"
          :active-item-client-id="activeItemClientId"
          :pois="poiCatalog"
          :poi-loading="poiLoading"
          :poi-error="poiError"
          @update:active-day="activeDay = $event"
          @select-item="selectItem"
          @delete-item="deleteDraftItem"
          @patch-item="patchItem"
          @reorder-day="reorderDay($event.dayIndex, $event.orderedClientIds)"
          @add-item="addItem"
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

