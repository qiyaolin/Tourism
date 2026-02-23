<script setup lang="ts">
import { computed } from "vue";

import type { ItineraryItemWithPoi, PublicItineraryResponse } from "../api";

const props = defineProps<{
  itinerary: PublicItineraryResponse;
  items: ItineraryItemWithPoi[];
  shareUrl: string;
}>();

const dayGroups = computed(() => {
  const grouped = new Map<number, ItineraryItemWithPoi[]>();
  for (const item of props.items) {
    if (!grouped.has(item.day_index)) {
      grouped.set(item.day_index, []);
    }
    grouped.get(item.day_index)?.push(item);
  }
  return Array.from(grouped.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([dayIndex, groupItems]) => ({
      dayIndex,
      items: groupItems.sort((a, b) => a.sort_order - b.sort_order),
    }));
});

const generatedAtText = computed(() =>
  new Date().toLocaleString("zh-CN", {
    hour12: false,
  })
);

function formatMoney(value: number | null): string {
  if (value == null) {
    return "未提供";
  }
  return `¥${value}`;
}
</script>

<template>
  <article class="export-poster">
    <header class="export-poster-header">
      <p class="export-kicker">Project Atlas 行程海报</p>
      <h1>{{ itinerary.title }}</h1>
      <p class="export-meta">{{ itinerary.destination }} · {{ itinerary.days }} 天 · 作者 {{ itinerary.author_nickname }}</p>
      <p class="export-link">公开链接：{{ shareUrl }}</p>
    </header>

    <section
      v-for="group in dayGroups"
      :key="group.dayIndex"
      class="export-day"
    >
      <h2>Day {{ group.dayIndex }}</h2>
      <article
        v-for="item in group.items"
        :key="item.item_id"
        class="export-block"
      >
        <div class="export-block-head">
          <h3>{{ item.poi.name }}</h3>
          <p>{{ item.poi.type }}</p>
        </div>
        <div class="export-grid">
          <p><strong>开始时间：</strong>{{ item.start_time || "未提供" }}</p>
          <p><strong>停留时长：</strong>{{ item.duration_minutes == null ? "未提供" : `${item.duration_minutes} 分钟` }}</p>
          <p><strong>预算花费：</strong>{{ formatMoney(item.cost) }}</p>
          <p><strong>参考票价：</strong>{{ formatMoney(item.poi.ticket_price) }}</p>
          <p><strong>地址：</strong>{{ item.poi.address || "未提供" }}</p>
          <p><strong>营业时间：</strong>{{ item.poi.opening_hours || "未提供" }}</p>
        </div>
        <p
          v-if="item.tips"
          class="export-tips"
        >
          建议：{{ item.tips }}
        </p>
      </article>
    </section>

    <footer class="export-footer">生成时间：{{ generatedAtText }}</footer>
  </article>
</template>

<style scoped>
.export-poster {
  width: 900px;
  background: #fff;
  color: #19262b;
  font-family: "Noto Sans SC", sans-serif;
  border: 1px solid #d8d2c5;
  border-radius: 24px;
  padding: 28px;
}

.export-poster-header {
  border-bottom: 1px solid #e5dfd2;
  padding-bottom: 16px;
}

.export-kicker {
  margin: 0;
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #5b686e;
}

h1 {
  margin: 8px 0 0;
  font-family: "Outfit", sans-serif;
  font-size: 34px;
}

.export-meta {
  margin: 8px 0 0;
  color: #36484f;
}

.export-link {
  margin: 8px 0 0;
  color: #4f6066;
  word-break: break-all;
}

.export-day {
  margin-top: 20px;
}

h2 {
  margin: 0 0 10px;
  font-family: "Outfit", sans-serif;
  font-size: 24px;
}

.export-block {
  border: 1px solid #e4ddcf;
  border-radius: 16px;
  padding: 14px;
  background: linear-gradient(180deg, #fffdf7 0%, #fff 100%);
}

.export-block + .export-block {
  margin-top: 10px;
}

.export-block-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 10px;
}

h3 {
  margin: 0;
  font-size: 20px;
  font-family: "Outfit", sans-serif;
}

.export-block-head p {
  margin: 0;
  color: #4d5f65;
}

.export-grid {
  margin-top: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px 12px;
}

.export-grid p {
  margin: 0;
  font-size: 14px;
}

.export-tips {
  margin: 10px 0 0;
  border-radius: 10px;
  padding: 8px 10px;
  background: #edf8f4;
  color: #205f53;
}

.export-footer {
  margin-top: 18px;
  border-top: 1px solid #e5dfd2;
  padding-top: 12px;
  font-size: 13px;
  color: #5a676d;
}
</style>
