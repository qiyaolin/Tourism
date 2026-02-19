<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import {
  fetchPublicItinerary,
  fetchPublicItineraryItemsWithPoi,
  forkPublicItinerary,
  type ItineraryItemWithPoi,
  type PublicItineraryResponse
} from "../api";
import PoiInfoCard from "../components/PoiInfoCard.vue";
import { useAuth } from "../composables/useAuth";
import { useAmap } from "../composables/useAmap";

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

const selectedItem = computed(
  () => items.value.find((item) => item.item_id === activeItemId.value) ?? null
);
const { token, isLoggedIn, loadMe } = useAuth();

const { mapReady, initMap, renderMarkers, focusMarker, clearMarkers, destroyMap } = useAmap(mapHost);

async function loadPageData() {
  const itineraryId = String(route.params.id || "");
  if (!itineraryId) {
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const [itineraryResult, itemResult] = await Promise.all([
      fetchPublicItinerary(itineraryId),
      fetchPublicItineraryItemsWithPoi(itineraryId)
    ]);
    itinerary.value = itineraryResult;
    items.value = itemResult.items;
    activeItemId.value = itemResult.items[0]?.item_id ?? "";
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载公开行程失败";
  } finally {
    loading.value = false;
  }
}

function onSelectItem(itemId: string) {
  activeItemId.value = itemId;
  focusMarker(itemId);
}

async function handleFork() {
  const itineraryId = String(route.params.id || "");
  if (!itineraryId) {
    return;
  }
  if (!isLoggedIn.value || !token.value) {
    await router.push(`/login?fork_source=${itineraryId}&redirect=${encodeURIComponent(route.fullPath)}`);
    return;
  }
  forkPending.value = true;
  forkError.value = "";
  try {
    const result = await forkPublicItinerary(itineraryId, token.value);
    await router.push(`/editor?itinerary_id=${result.new_itinerary_id}`);
  } catch (e) {
    forkError.value = e instanceof Error ? e.message : "借鉴失败";
  } finally {
    forkPending.value = false;
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
      </div>
      <p
        v-if="forkError"
        class="error"
      >
        {{ forkError }}
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
