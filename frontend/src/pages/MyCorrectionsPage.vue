<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { fetchMyCorrections, type PoiCorrectionResponse } from "../api";
import { useAuth } from "../composables/useAuth";

const loading = ref(false);
const error = ref("");
const items = ref<PoiCorrectionResponse[]>([]);

const { token, loadMe } = useAuth();

function statusText(status: PoiCorrectionResponse["status"]) {
  if (status === "accepted") return "已采纳";
  if (status === "rejected") return "已驳回";
  return "待审核";
}

function formatRuleSummary(raw: string | null): string {
  if (!raw) {
    return "未填写";
  }
  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return raw;
    }
    if (parsed.length === 0) {
      return "未填写";
    }
    return parsed
      .map((r) => {
        if (!r || typeof r !== "object") {
          return "无效规则";
        }
        const row = r as Record<string, unknown>;
        const audience = typeof row.audience_code === "string" ? row.audience_code : "unknown";
        const ticketType = typeof row.ticket_type === "string" ? row.ticket_type : "未知票种";
        const timeSlot = typeof row.time_slot === "string" ? row.time_slot : "未知时段";
        const price = typeof row.price === "number" ? row.price : Number(row.price ?? 0);
        const conditions = typeof row.conditions === "string" && row.conditions ? `（${row.conditions}）` : "";
        return `${audience}/${ticketType}/${timeSlot}: ¥${Number.isFinite(price) ? price : 0}${conditions}`;
      })
      .join("；");
  } catch {
    return raw;
  }
}

const orderedItems = computed(() =>
  items.value.slice().sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
);

async function loadCorrections() {
  if (!token.value) {
    return;
  }
  loading.value = true;
  error.value = "";
  try {
    const result = await fetchMyCorrections(token.value, 0, 50);
    items.value = result.items;
  } catch (e) {
    error.value = e instanceof Error ? e.message : "加载我的纠错失败";
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  await loadMe();
  await loadCorrections();
});
</script>

<template>
  <main class="atlas-root">
    <header class="topbar">
      <div>
        <p class="kicker">Corrections</p>
        <h1>我的纠错记录</h1>
      </div>
      <button class="btn ghost" :disabled="loading" @click="loadCorrections">
        刷新
      </button>
    </header>

    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="loading" class="subtle">加载中...</p>
    <p v-else-if="orderedItems.length === 0" class="subtle">暂无纠错记录。</p>

    <section class="mine-sections" v-else>
      <article v-for="item in orderedItems" :key="item.id" class="mine-card">
        <h3>{{ item.type_label }}</h3>
        <p class="subtle">状态：{{ statusText(item.status) }}</p>
        <p class="subtle">纠错景点：{{ item.source_poi_name_snapshot || item.poi_id }}</p>
        <p class="subtle">
          来源模板：
          <span v-if="item.source_itinerary_title_snapshot">
            {{ item.source_itinerary_title_snapshot }}
            <span v-if="item.source_itinerary_author_snapshot">（作者：{{ item.source_itinerary_author_snapshot }}）</span>
          </span>
          <span v-else>未关联模板</span>
        </p>
        <p class="subtle">规则内容：{{ formatRuleSummary(item.proposed_value) }}</p>
        <p class="subtle">补充说明：{{ item.details || "无" }}</p>
        <p v-if="item.review_comment" class="subtle">审核备注：{{ item.review_comment }}</p>
        <p class="subtle">提交时间：{{ new Date(item.created_at).toLocaleString() }}</p>
        <a v-if="item.photo_url" class="btn ghost" :href="item.photo_url" target="_blank" rel="noreferrer">查看图片证据</a>
      </article>
    </section>
  </main>
</template>
