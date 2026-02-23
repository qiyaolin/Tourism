<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import {
  fetchExploreHeatmap,
  fetchExploreRecommendations,
  fetchNotifications,
  fetchPublicItineraries,
  type ExploreHeatPointResponse,
  type ExploreRecommendationItemResponse,
  type PublicItineraryResponse
} from "../api";
import { useAuth } from "../composables/useAuth";

const TEXT = {
  kicker: "探索广场",
  title: "探索广场",
  refresh: "刷新",
  refreshing: "刷新中...",
  signalTitle: "预警中心",
  unread: "未读通知",
  open: "查看",
  intro: "公开发布的行程会展示在这里，并按热度与偏好为你推荐。",
  loadFailed: "加载探索广场失败",
  author: "作者",
  detail: "浏览详情",
  forked: "借鉴",
  emptyTitle: "暂无公开行程",
  emptyDesc: "还没有用户发布公开行程。",
  daySuffix: "天",
  heatTitle: "全站足迹热力图",
  heatHint: "根据公开行程的访问记录聚合",
  trendTitle: "借鉴趋势榜",
  trendHint: "按借鉴次数与近期热度排序",
  recommendationTitle: "智能推荐",
  recommendationHint: "根据你的浏览偏好和社区热度生成",
  noVisitTag: "暂无访问记录"
} as const;

const { token, isLoggedIn } = useAuth();
const loading = ref(false);
const error = ref("");
const itineraries = ref<PublicItineraryResponse[]>([]);
const heatPoints = ref<ExploreHeatPointResponse[]>([]);
const recommendations = ref<ExploreRecommendationItemResponse[]>([]);
const unreadCount = ref(0);

const hasData = computed(() => itineraries.value.length > 0);
const trendItems = computed(() =>
  [...itineraries.value]
    .sort(
      (a, b) =>
        b.forked_count - a.forked_count ||
        Date.parse(b.updated_at) - Date.parse(a.updated_at)
    )
    .slice(0, 6)
);
const maxHeatScore = computed(() => Math.max(1, ...heatPoints.value.map((point) => point.heat_score)));
const recommendationItems = computed(() => recommendations.value.slice(0, 6));
const showRecommendation = computed(() => recommendationItems.value.length > 0);

function formatRecentVisitLabel(lastVisitedAt: string | null): string {
  if (!lastVisitedAt) {
    return TEXT.noVisitTag;
  }
  const visitDate = new Date(lastVisitedAt);
  if (Number.isNaN(visitDate.getTime())) {
    return TEXT.noVisitTag;
  }
  const diffMs = Date.now() - visitDate.getTime();
  if (diffMs < 60 * 60 * 1000) {
    return "刚刚有人去过";
  }
  const hours = Math.floor(diffMs / (60 * 60 * 1000));
  if (hours < 24) {
    return `${hours} 小时前有人去过`;
  }
  const days = Math.floor(hours / 24);
  if (days <= 30) {
    return `${days} 天前有人去过`;
  }
  const month = String(visitDate.getMonth() + 1).padStart(2, "0");
  const day = String(visitDate.getDate()).padStart(2, "0");
  return `${visitDate.getFullYear()}-${month}-${day} 有人去过`;
}

function heatBarWidth(score: number): string {
  const ratio = score / maxHeatScore.value;
  return `${Math.max(8, Math.round(ratio * 100))}%`;
}

async function loadExploreData() {
  loading.value = true;
  error.value = "";
  try {
    const [publicResult, heatmapResult, recommendationResult] = await Promise.all([
      fetchPublicItineraries(0, 60),
      fetchExploreHeatmap(20),
      fetchExploreRecommendations(12, token.value || undefined)
    ]);
    itineraries.value = publicResult.items;
    heatPoints.value = heatmapResult.items;
    recommendations.value = recommendationResult.items;
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
  void loadExploreData();
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
      <button class="btn ghost" :disabled="loading" @click="loadExploreData">
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

    <section class="explore-insights">
      <article class="panel-card insight-card">
        <div class="insight-head">
          <h2>{{ TEXT.heatTitle }}</h2>
          <p class="subtle">{{ TEXT.heatHint }}</p>
        </div>
        <div v-if="heatPoints.length === 0" class="empty-note">{{ TEXT.emptyDesc }}</div>
        <ol v-else class="heat-list">
          <li v-for="point in heatPoints" :key="point.poi_id" class="heat-item">
            <div class="heat-meta">
              <strong>{{ point.name }}</strong>
              <span>{{ point.heat_score }}</span>
            </div>
            <div class="heat-bar-track">
              <span class="heat-bar-fill" :style="{ width: heatBarWidth(point.heat_score) }" />
            </div>
          </li>
        </ol>
      </article>

      <article class="panel-card insight-card">
        <div class="insight-head">
          <h2>{{ TEXT.trendTitle }}</h2>
          <p class="subtle">{{ TEXT.trendHint }}</p>
        </div>
        <div v-if="trendItems.length === 0" class="empty-note">{{ TEXT.emptyDesc }}</div>
        <ol v-else class="trend-list">
          <li v-for="(itinerary, index) in trendItems" :key="itinerary.id" class="trend-item">
            <span class="trend-rank">#{{ index + 1 }}</span>
            <div class="trend-body">
              <h3>{{ itinerary.title }}</h3>
              <p class="subtle">{{ itinerary.destination }} · {{ itinerary.days }} {{ TEXT.daySuffix }}</p>
              <p class="subtle">{{ TEXT.forked }}：{{ itinerary.forked_count }}</p>
              <p class="subtle">{{ formatRecentVisitLabel(itinerary.last_visited_at) }}</p>
            </div>
            <RouterLink class="btn ghost" :to="`/itineraries/${itinerary.id}`">{{ TEXT.detail }}</RouterLink>
          </li>
        </ol>
      </article>
    </section>

    <section v-if="showRecommendation" class="panel-card recommendation-panel">
      <div class="insight-head">
        <h2>{{ TEXT.recommendationTitle }}</h2>
        <p class="subtle">{{ TEXT.recommendationHint }}</p>
      </div>
      <div class="recommendation-list">
        <article v-for="item in recommendationItems" :key="item.itinerary.id" class="recommendation-card">
          <h3>{{ item.itinerary.title }}</h3>
          <p class="subtle">{{ item.itinerary.destination }} · {{ item.itinerary.days }} {{ TEXT.daySuffix }}</p>
          <p class="subtle">{{ formatRecentVisitLabel(item.itinerary.last_visited_at) }}</p>
          <div class="reason-tags">
            <span v-for="reason in item.reasons" :key="reason" class="reason-tag">{{ reason }}</span>
          </div>
          <RouterLink class="btn primary" :to="`/itineraries/${item.itinerary.id}`">{{ TEXT.detail }}</RouterLink>
        </article>
      </div>
    </section>

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
          <p class="subtle">{{ TEXT.forked }}：{{ itinerary.forked_count }}</p>
          <p class="visit-tag">{{ formatRecentVisitLabel(itinerary.last_visited_at) }}</p>
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
