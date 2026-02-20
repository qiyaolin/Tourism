<script setup lang="ts">
import type { ItineraryWeatherDayResponse } from "../api";

defineProps<{
  loading: boolean;
  error: string;
  hasStartDate: boolean;
  items: ItineraryWeatherDayResponse[];
}>();

const emit = defineEmits<{
  (event: "retry"): void;
}>();

function formatTemperature(item: ItineraryWeatherDayResponse): string {
  if (item.temp_min === null || item.temp_max === null) {
    return "--";
  }
  return `${item.temp_min}~${item.temp_max}°C`;
}
</script>

<template>
  <section class="weather-strip panel-card">
    <div class="weather-strip-head">
      <div>
        <h3>天气预报</h3>
        <p class="subtle">
          按行程 Day 显示对应日期天气
        </p>
      </div>
      <button
        class="btn ghost"
        type="button"
        :disabled="loading"
        @click="emit('retry')"
      >
        {{ loading ? "刷新中..." : "重试" }}
      </button>
    </div>

    <p
      v-if="!hasStartDate"
      class="empty-note"
    >
      请先设置行程开始日期后查看天气。
    </p>
    <p
      v-else-if="error"
      class="error"
    >
      天气暂不可用：{{ error }}
    </p>
    <p
      v-else-if="loading"
      class="subtle"
    >
      正在获取天气...
    </p>
    <div
      v-else
      class="weather-row"
    >
      <article
        v-for="item in items"
        :key="`${item.day_index}-${item.date}`"
        class="weather-card"
      >
        <p class="weather-day">
          Day {{ item.day_index }}
        </p>
        <p class="weather-date">
          {{ item.date }}
        </p>
        <p class="weather-text">
          {{ item.text }}
        </p>
        <p class="weather-temp">
          {{ formatTemperature(item) }}
        </p>
      </article>
    </div>
  </section>
</template>
