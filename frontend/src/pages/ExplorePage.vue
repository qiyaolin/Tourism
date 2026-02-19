<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchPublicItineraries, type PublicItineraryResponse } from "../api";

const loading = ref(false);
const error = ref("");
const itineraries = ref<PublicItineraryResponse[]>([]);

const hasData = computed(() => itineraries.value.length > 0);

async function loadPublicItineraries() {
  loading.value = true;
  error.value = "";
  try {
    const result = await fetchPublicItineraries(0, 60);
    itineraries.value = result.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载探索广场失败";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void loadPublicItineraries();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">
          Explore Square
        </p>
        <h1>探索广场</h1>
      </div>
      <button
        class="btn ghost"
        :disabled="loading"
        @click="loadPublicItineraries"
      >
        {{ loading ? "刷新中..." : "刷新" }}
      </button>
    </header>
    <p class="subtle">
      公开发布的行程会在这里展示，可直接浏览详情。
    </p>
    <p
      v-if="error"
      class="error"
    >
      {{ error }}
    </p>
    <section
      v-if="hasData"
      class="explore-grid"
    >
      <article
        v-for="itinerary in itineraries"
        :key="itinerary.id"
        class="explore-card"
      >
        <div
          class="explore-cover"
          :style="itinerary.cover_image_url ? `background-image:url(${itinerary.cover_image_url})` : ''"
        />
        <div class="explore-content">
          <h2>{{ itinerary.title }}</h2>
          <p class="subtle">
            {{ itinerary.destination }} · {{ itinerary.days }} 天
          </p>
          <p class="subtle">
            作者：{{ itinerary.author_nickname }}
          </p>
          <RouterLink
            class="btn primary"
            :to="`/itineraries/${itinerary.id}`"
          >
            浏览详情
          </RouterLink>
        </div>
      </article>
    </section>
    <section
      v-else-if="!loading && !error"
      class="panel-card"
    >
      <h2>暂无公开行程</h2>
      <p class="empty-note">
        还没有用户发布公开行程，稍后再来看看。
      </p>
    </section>
  </main>
</template>
