<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  fetchPublicItinerary,
  fetchPublicItineraryShareMeta,
  fetchPublicItineraryItemsWithPoi,
  forkPublicItinerary,
  recordPublicItineraryView,
  type ItineraryItemWithPoi,
  type PublicItineraryResponse,
  type PublicItineraryShareMetaResponse
} from "../api";
import PoiInfoCard from "../components/PoiInfoCard.vue";
import { useAuth } from "../composables/useAuth";
import { useAmap } from "../composables/useAmap";
import { exportItineraryPdf, exportItineraryPosterPng } from "../utils/itineraryExport";

const route = useRoute();
const router = useRouter();
const itinerary = ref<PublicItineraryResponse | null>(null);
const items = ref<ItineraryItemWithPoi[]>([]);
const activeItemId = ref("");
const loading = ref(false);
const error = ref("");
const mapHost = ref<HTMLElement | null>(null);
const mapLoading = ref(false);
const mapError = ref("");
const forkPending = ref(false);
const forkError = ref("");
const shareMeta = ref<PublicItineraryShareMetaResponse | null>(null);
const exportPending = ref(false);
const exportError = ref("");
const exportSuccess = ref("");
const viewLogReportedItineraryId = ref("");

const selectedItem = computed(
  () => items.value.find((item) => item.item_id === activeItemId.value) ?? null
);
const itineraryId = computed(() => String(route.params.id || ""));
const publicShareUrl = computed(() => {
  if (shareMeta.value?.public_url) {
    return shareMeta.value.public_url;
  }
  if (!itineraryId.value) {
    return "";
  }
  return `${window.location.origin}/itineraries/${itineraryId.value}`;
});
const shareCardUrl = computed(() => shareMeta.value?.share_card_url ?? "");
const { token, isLoggedIn, loadMe } = useAuth();

const { mapReady, initMap, renderMarkers, focusMarker, clearMarkers, destroyMap } = useAmap(mapHost);

async function loadPageData() {
  if (!itineraryId.value) {
    return;
  }
  loading.value = true;
  error.value = "";
  exportError.value = "";
  exportSuccess.value = "";
  try {
    const [itineraryResult, itemResult] = await Promise.all([
      fetchPublicItinerary(itineraryId.value),
      fetchPublicItineraryItemsWithPoi(itineraryId.value)
    ]);
    itinerary.value = itineraryResult;
    items.value = itemResult.items;
    activeItemId.value = itemResult.items[0]?.item_id ?? "";
    await reportViewIfNeeded();
    try {
      shareMeta.value = await fetchPublicItineraryShareMeta(itineraryId.value);
    } catch {
      shareMeta.value = null;
    }
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载公开行程失败";
  } finally {
    loading.value = false;
  }
}

async function reportViewIfNeeded() {
  if (!itineraryId.value || !token.value) {
    return;
  }
  if (viewLogReportedItineraryId.value === itineraryId.value) {
    return;
  }
  try {
    await recordPublicItineraryView(itineraryId.value, token.value);
    viewLogReportedItineraryId.value = itineraryId.value;
  } catch {
    // Ignore view-log failures to avoid breaking main page load path.
  }
}

function onSelectItem(itemId: string) {
  activeItemId.value = itemId;
  focusMarker(itemId);
}

async function handleFork() {
  if (!itineraryId.value) {
    return;
  }
  if (!isLoggedIn.value || !token.value) {
    await router.push(`/login?fork_source=${itineraryId.value}&redirect=${encodeURIComponent(route.fullPath)}`);
    return;
  }
  forkPending.value = true;
  forkError.value = "";
  try {
    const result = await forkPublicItinerary(itineraryId.value, token.value);
    await router.push(`/editor?itinerary_id=${result.new_itinerary_id}`);
  } catch (e) {
    forkError.value = e instanceof Error ? e.message : "借鉴失败";
  } finally {
    forkPending.value = false;
  }
}

async function handleExportPng() {
  if (!itinerary.value) {
    exportError.value = "导出失败：行程内容未加载完成";
    return;
  }
  exportPending.value = true;
  exportError.value = "";
  exportSuccess.value = "";
  try {
    await exportItineraryPosterPng({
      data: {
        title: itinerary.value.title,
        destination: itinerary.value.destination,
        days: itinerary.value.days,
        author_nickname: itinerary.value.author_nickname,
        share_url: publicShareUrl.value,
        items: items.value,
      },
      fileBaseName: `${itinerary.value.title}-行程海报`,
    });
    exportSuccess.value = "长图已导出";
  } catch (e) {
    exportError.value = e instanceof Error ? e.message : "长图导出失败，请稍后重试";
  } finally {
    exportPending.value = false;
  }
}

async function handleExportPdf() {
  if (!itinerary.value) {
    exportError.value = "导出失败：行程内容未加载完成";
    return;
  }
  exportPending.value = true;
  exportError.value = "";
  exportSuccess.value = "";
  try {
    await exportItineraryPdf({
      data: {
        title: itinerary.value.title,
        destination: itinerary.value.destination,
        days: itinerary.value.days,
        author_nickname: itinerary.value.author_nickname,
        share_url: publicShareUrl.value,
        items: items.value,
      },
      fileBaseName: `${itinerary.value.title}-行程文档`,
    });
    exportSuccess.value = "已打开打印窗口，请选择“保存为 PDF”";
  } catch (e) {
    exportError.value = e instanceof Error ? e.message : "PDF 导出失败，请稍后重试";
  } finally {
    exportPending.value = false;
  }
}

async function handleCopyPublicShareLink() {
  if (!publicShareUrl.value) {
    exportError.value = "复制失败：分享链接不可用";
    return;
  }
  exportError.value = "";
  exportSuccess.value = "";
  try {
    await navigator.clipboard.writeText(publicShareUrl.value);
    exportSuccess.value = "公开分享链接已复制";
  } catch {
    exportError.value = "复制失败，请手动复制链接";
  }
}

async function handleCopyShareCardLink() {
  if (!shareCardUrl.value) {
    exportError.value = "复制失败：微信卡片链接不可用";
    return;
  }
  exportError.value = "";
  exportSuccess.value = "";
  try {
    await navigator.clipboard.writeText(shareCardUrl.value);
    exportSuccess.value = "微信卡片链接已复制";
  } catch {
    exportError.value = "复制失败，请手动复制链接";
  }
}

async function tryAutoForkAfterLogin() {
  const autoFork = String(route.query.auto_fork || "");
  if (autoFork !== "1") {
    return;
  }
  if (!isLoggedIn.value) {
    await loadMe();
  }
  if (!isLoggedIn.value || !token.value) {
    return;
  }
  await router.replace({ path: route.path, query: {} });
  await handleFork();
}

async function setupMap() {
  mapLoading.value = true;
  mapError.value = "";
  try {
    await initMap();
  } catch (e) {
    mapError.value = e instanceof Error ? e.message : "地图加载失败";
  } finally {
    mapLoading.value = false;
  }
}

watch(
  () => items.value,
  (value) => {
    if (!mapReady.value) {
      return;
    }
    renderMarkers(value, (item) => {
      activeItemId.value = item.item_id;
    });
    if (activeItemId.value) {
      focusMarker(activeItemId.value);
    }
  },
  { deep: true }
);

onMounted(async () => {
  await Promise.all([loadPageData(), setupMap()]);
  await tryAutoForkAfterLogin();
});

onBeforeUnmount(() => {
  clearMarkers();
  destroyMap();
});
</script>

<template>
  <main class="atlas-root">
    <section class="panel-card">
      <h2 v-if="itinerary">
        {{ itinerary.title }}
      </h2>
      <p class="subtle">
        <template v-if="itinerary">
          {{ itinerary.destination }} · {{ itinerary.days }} 天 · 作者 {{ itinerary.author_nickname }}
        </template>
      </p>
      <p
        v-if="loading"
        class="subtle"
      >
        加载中...
      </p>
      <p
        v-if="error"
        class="error"
      >
        {{ error }}
      </p>
      <div class="action-row">
        <button
          class="btn primary"
          :disabled="forkPending || loading"
          @click="handleFork"
        >
          {{ forkPending ? "借鉴中..." : "以此为模板" }}
        </button>
        <button
          class="btn"
          :disabled="exportPending || loading"
          @click="handleExportPng"
        >
          {{ exportPending ? "导出中..." : "导出长图" }}
        </button>
        <button
          class="btn"
          :disabled="exportPending || loading"
          @click="handleExportPdf"
        >
          {{ exportPending ? "导出中..." : "导出 PDF" }}
        </button>
        <button
          class="btn ghost"
          :disabled="loading"
          @click="handleCopyPublicShareLink"
        >
          复制分享链接
        </button>
        <button
          class="btn ghost"
          :disabled="loading || !shareCardUrl"
          @click="handleCopyShareCardLink"
        >
          复制微信卡片链接
        </button>
      </div>
      <p
        v-if="exportSuccess"
        class="subtle"
      >
        {{ exportSuccess }}
      </p>
      <p
        v-if="forkError || exportError"
        class="error"
      >
        {{ forkError || exportError }}
      </p>
    </section>

    <section class="public-layout">
      <div class="panel-card">
        <h2>时间轴（只读）</h2>
        <div
          v-if="items.length === 0 && !loading"
          class="empty-note"
        >
          当前公开行程暂无时间块。
        </div>
        <div class="timeline-list">
          <article
            v-for="item in items"
            :key="item.item_id"
            class="timeline-block"
            :class="{ active: activeItemId === item.item_id }"
            @click="onSelectItem(item.item_id)"
          >
            <p class="timeline-block-order">
              Day {{ item.day_index }} · #{{ item.sort_order }}
            </p>
            <h3 class="timeline-block-title">
              {{ item.poi.name }}
            </h3>
            <p class="timeline-block-type">
              {{ item.poi.type }}
            </p>
          </article>
        </div>
      </div>

      <section class="editor-panel">
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
          v-if="selectedItem"
          :item="selectedItem"
        />
      </section>
    </section>
  </main>
</template>
