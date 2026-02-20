<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchNotifications, fetchPublicItineraries, type PublicItineraryResponse } from "../api";
import { useAuth } from "../composables/useAuth";

const TEXT = {
  kicker: "\u63a2\u7d22\u5e7f\u573a",
  title: "\u63a2\u7d22\u5e7f\u573a",
  refresh: "\u5237\u65b0",
  refreshing: "\u5237\u65b0\u4e2d...",
  signalTitle: "\u9884\u8b66\u4e2d\u5fc3",
  unread: "\u672a\u8bfb\u901a\u77e5",
  open: "\u67e5\u770b",
  intro: "\u516c\u5f00\u53d1\u5e03\u7684\u884c\u7a0b\u4f1a\u5c55\u793a\u5728\u8fd9\u91cc\uff0c\u53ef\u76f4\u63a5\u501f\u9274\u4e3a\u6a21\u677f\u3002",
  loadFailed: "\u52a0\u8f7d\u63a2\u7d22\u5e7f\u573a\u5931\u8d25",
  author: "\u4f5c\u8005",
  detail: "\u6d4f\u89c8\u8be6\u60c5",
  emptyTitle: "\u6682\u65e0\u516c\u5f00\u884c\u7a0b",
  emptyDesc: "\u8fd8\u6ca1\u6709\u7528\u6237\u53d1\u5e03\u516c\u5f00\u884c\u7a0b\u3002",
  daySuffix: "\u5929"
} as const;

const { token, isLoggedIn } = useAuth();
const loading = ref(false);
const error = ref("");
const itineraries = ref<PublicItineraryResponse[]>([]);
const unreadCount = ref(0);

const hasData = computed(() => itineraries.value.length > 0);

async function loadPublicItineraries() {
  loading.value = true;
  error.value = "";
  try {
    const result = await fetchPublicItineraries(0, 60);
    itineraries.value = result.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : TEXT.loadFailed;
  } finally {
    loading.value = false;
  }
}

async function loadNotificationSummary() {
  if (!token.value) {
    unreadCount.value = 0;
    return;
  }
  try {
    const data = await fetchNotifications(token.value, 0, 1, false);
    unreadCount.value = data.unread_count;
  } catch {
    unreadCount.value = 0;
  }
}

onMounted(() => {
  void loadPublicItineraries();
  void loadNotificationSummary();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">{{ TEXT.kicker }}</p>
        <h1>{{ TEXT.title }}</h1>
      </div>
      <button class="btn ghost" :disabled="loading" @click="loadPublicItineraries">
        {{ loading ? TEXT.refreshing : TEXT.refresh }}
      </button>
    </header>

    <section v-if="isLoggedIn" class="signal-entry panel-card">
      <div>
        <h2>{{ TEXT.signalTitle }}</h2>
        <p class="subtle">{{ TEXT.unread }}：{{ unreadCount }}</p>
      </div>
      <RouterLink class="btn primary" to="/notifications">{{ TEXT.open }}</RouterLink>
    </section>

    <p class="subtle">{{ TEXT.intro }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <section v-if="hasData" class="explore-grid">
      <article v-for="itinerary in itineraries" :key="itinerary.id" class="explore-card">
        <div
          class="explore-cover"
          :style="itinerary.cover_image_url ? `background-image:url(${itinerary.cover_image_url})` : ''"
        />
        <div class="explore-content">
          <h2>{{ itinerary.title }}</h2>
          <p class="subtle">{{ itinerary.destination }} · {{ itinerary.days }} {{ TEXT.daySuffix }}</p>
          <p class="subtle">{{ TEXT.author }}：{{ itinerary.author_nickname }}</p>
          <RouterLink class="btn primary" :to="`/itineraries/${itinerary.id}`">{{ TEXT.detail }}</RouterLink>
        </div>
      </article>
    </section>

    <section v-else-if="!loading && !error" class="panel-card">
      <h2>{{ TEXT.emptyTitle }}</h2>
      <p class="empty-note">{{ TEXT.emptyDesc }}</p>
    </section>
  </main>
</template>
